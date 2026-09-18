"""
tests/test_rate_limiter.py
===========================
Tests for the in-memory login rate limiter.
"""
import pytest
from app.services.rate_limiter import LoginRateLimiter


@pytest.fixture(autouse=True)
def fresh_limiter():
    """Each test gets an isolated limiter instance."""
    lim = LoginRateLimiter()
    yield lim


def test_normal_login_allowed(fresh_limiter):
    status = fresh_limiter.check('1.2.3.4')
    assert status['allowed']
    assert status['attempts'] == 0


def test_failure_counter_increments(fresh_limiter):
    fresh_limiter.record_failure('1.2.3.4')
    fresh_limiter.record_failure('1.2.3.4')
    s = fresh_limiter.check('1.2.3.4')
    assert s['attempts'] == 2
    assert s['allowed']


def test_lockout_after_max_attempts(fresh_limiter):
    from app.services.rate_limiter import MAX_ATTEMPTS
    for _ in range(MAX_ATTEMPTS):
        fresh_limiter.record_failure('192.168.1.1')
    s = fresh_limiter.check('192.168.1.1')
    assert not s['allowed']
    assert s['locked']
    assert s['retry_after'] > 0


def test_success_resets_counter(fresh_limiter):
    from app.services.rate_limiter import MAX_ATTEMPTS
    # Record several failures (but not enough to lock out)
    for _ in range(min(3, MAX_ATTEMPTS - 1)):
        fresh_limiter.record_failure('10.0.0.1')
    assert fresh_limiter.check('10.0.0.1')['attempts'] > 0
    # Successful login clears the counter
    fresh_limiter.record_success('10.0.0.1')
    s = fresh_limiter.check('10.0.0.1')
    assert s['attempts'] == 0
    assert s['allowed']


def test_different_ips_are_isolated(fresh_limiter):
    from app.services.rate_limiter import MAX_ATTEMPTS
    for _ in range(MAX_ATTEMPTS):
        fresh_limiter.record_failure('11.11.11.11')
    # Unrelated IP must still be allowed
    assert fresh_limiter.check('22.22.22.22')['allowed']
    # The locked IP must not be allowed
    assert not fresh_limiter.check('11.11.11.11')['allowed']


def test_clear_resets_all(fresh_limiter):
    from app.services.rate_limiter import MAX_ATTEMPTS
    for _ in range(MAX_ATTEMPTS):
        fresh_limiter.record_failure('5.5.5.5')
    assert not fresh_limiter.check('5.5.5.5')['allowed']
    fresh_limiter.clear()
    assert fresh_limiter.check('5.5.5.5')['allowed']


def test_lockout_triggers_on_threshold(fresh_limiter):
    from app.services.rate_limiter import MAX_ATTEMPTS
    for i in range(MAX_ATTEMPTS - 1):
        locked = fresh_limiter.record_failure('9.9.9.9')
        assert not locked, f"should not lock on attempt {i + 1}"
    newly_locked = fresh_limiter.record_failure('9.9.9.9')
    assert newly_locked, "should lock on the MAX_ATTEMPTS-th failure"
