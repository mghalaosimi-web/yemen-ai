"""
app/services/rate_limiter.py
==============================
Thread-safe in-memory brute-force protection for authentication endpoints.

Design decisions:
  • Pure Python, no Redis or external service — fully local.
  • Tracks failed attempts keyed by (ip, username) independently.
  • Expired attempt windows are pruned lazily on each check call.
  • A successful login resets the IP counter so legitimate users are
    never permanently locked out.
  • Limits are configurable via environment variables at import time.
"""
from __future__ import annotations
import threading
import time
import os
from collections import defaultdict

# ── Configuration ─────────────────────────────────────────────────────────────
# Maximum failed attempts before lockout (per IP).
MAX_ATTEMPTS = int(os.getenv('YEMEN_AI_LOGIN_MAX_ATTEMPTS', '10'))
# Window in seconds over which attempts are counted.
WINDOW_SECONDS = int(os.getenv('YEMEN_AI_LOGIN_WINDOW_SECONDS', '300'))   # 5 min
# How long a locked IP must wait before retrying.
LOCKOUT_SECONDS = int(os.getenv('YEMEN_AI_LOGIN_LOCKOUT_SECONDS', '600'))  # 10 min


class _AttemptBucket:
    """Sliding-window counter for a single (ip, username) key."""
    __slots__ = ('timestamps', 'locked_until')

    def __init__(self):
        self.timestamps: list[float] = []
        self.locked_until: float = 0.0

    def _prune(self, now: float) -> None:
        cutoff = now - WINDOW_SECONDS
        self.timestamps = [t for t in self.timestamps if t > cutoff]

    def is_locked(self, now: float) -> bool:
        return now < self.locked_until

    def record_failure(self, now: float) -> bool:
        """Record a failure; returns True if the IP should now be locked."""
        self._prune(now)
        self.timestamps.append(now)
        if len(self.timestamps) >= MAX_ATTEMPTS:
            self.locked_until = now + LOCKOUT_SECONDS
            self.timestamps.clear()
            return True
        return False

    def reset(self, now: float) -> None:
        """Call on successful login to clear failure history."""
        self._prune(now)
        self.timestamps.clear()
        self.locked_until = 0.0

    def attempts_in_window(self, now: float) -> int:
        self._prune(now)
        return len(self.timestamps)

    def seconds_until_unlock(self, now: float) -> int:
        return max(0, int(self.locked_until - now))


class LoginRateLimiter:
    """
    Process-global rate limiter.  A single instance should be shared
    across all requests (use the module-level `limiter` singleton).
    """

    def __init__(self):
        self._lock = threading.Lock()
        # Keys are (ip: str, username: str).  username='' tracks IP-only.
        self._buckets: dict[tuple[str, str], _AttemptBucket] = defaultdict(_AttemptBucket)

    def _bucket(self, ip: str, username: str = '') -> _AttemptBucket:
        return self._buckets[(ip, username)]

    def check(self, ip: str, username: str = '') -> dict:
        """
        Check whether this IP (and optionally username) is allowed to attempt
        login.

        Returns a dict with:
          allowed: bool
          locked_until: float  (epoch; 0 if not locked)
          attempts: int        (failures in current window)
          retry_after: int     (seconds; 0 if not locked)
        """
        now = time.monotonic()
        with self._lock:
            ip_bucket = self._bucket(ip, '')
            user_bucket = self._bucket(ip, username) if username else ip_bucket
            ip_locked = ip_bucket.is_locked(now)
            user_locked = user_bucket.is_locked(now) if username else False
            locked = ip_locked or user_locked
            retry_after = max(
                ip_bucket.seconds_until_unlock(now),
                user_bucket.seconds_until_unlock(now) if username else 0,
            )
            attempts = ip_bucket.attempts_in_window(now)
        return {
            'allowed': not locked,
            'locked': locked,
            'attempts': attempts,
            'retry_after': retry_after,
        }

    def record_failure(self, ip: str, username: str = '') -> bool:
        """
        Record a failed login attempt.

        Returns True if the IP is now locked (just crossed the threshold).
        """
        now = time.monotonic()
        newly_locked = False
        with self._lock:
            if self._bucket(ip, '').record_failure(now):
                newly_locked = True
            if username:
                self._bucket(ip, username).record_failure(now)
        return newly_locked

    def record_success(self, ip: str, username: str = '') -> None:
        """Reset counters on successful login."""
        now = time.monotonic()
        with self._lock:
            self._bucket(ip, '').reset(now)
            if username:
                self._bucket(ip, username).reset(now)

    def status(self, ip: str, username: str = '') -> dict:
        """Diagnostic info for a specific IP."""
        now = time.monotonic()
        with self._lock:
            bucket = self._bucket(ip, '')
            return {
                'ip': ip,
                'username': username or None,
                'locked': bucket.is_locked(now),
                'attempts': bucket.attempts_in_window(now),
                'retry_after': bucket.seconds_until_unlock(now),
                'config': {
                    'max_attempts': MAX_ATTEMPTS,
                    'window_seconds': WINDOW_SECONDS,
                    'lockout_seconds': LOCKOUT_SECONDS,
                },
            }

    def clear(self) -> None:
        """Reset all state — useful in tests."""
        with self._lock:
            self._buckets.clear()


# Module-level singleton
limiter = LoginRateLimiter()
