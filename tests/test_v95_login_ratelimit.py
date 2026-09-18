"""
tests/test_v95_login_ratelimit.py
==================================
Integration tests for the login rate limiter via the HTTP API.

These tests use the module-level limiter singleton directly to reset state
between tests so they don't interfere with the existing auth test suite.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.rate_limiter import limiter as _limiter, MAX_ATTEMPTS

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_limiter():
    """Reset rate limiter state before every test to prevent cross-test contamination."""
    _limiter.clear()
    yield
    _limiter.clear()


def test_normal_login_passes():
    r = client.post('/api/auth/login', json={'username': 'user', 'password': 'YemenAI2026!'})
    assert r.status_code == 200


def test_failed_login_returns_401():
    r = client.post('/api/auth/login', json={'username': 'user', 'password': 'wrong'})
    assert r.status_code == 401
    # Must not leak username existence vs wrong password
    assert 'Invalid credentials' in r.json().get('detail', '')


def test_lockout_after_max_attempts():
    """After MAX_ATTEMPTS failures the next attempt should return 429."""
    for _ in range(MAX_ATTEMPTS):
        client.post('/api/auth/login', json={'username': 'nobody', 'password': 'bad'})
    r = client.post('/api/auth/login', json={'username': 'nobody', 'password': 'bad'})
    assert r.status_code == 429
    body = r.json()
    assert 'detail' in body


def test_successful_login_clears_counter():
    """Failed attempts followed by a successful login should reset the counter."""
    for _ in range(min(3, MAX_ATTEMPTS - 1)):
        client.post('/api/auth/login', json={'username': 'admin', 'password': 'wrong'})
    r = client.post('/api/auth/login', json={'username': 'admin', 'password': 'YemenAI2026!'})
    assert r.status_code == 200
    # Subsequent attempt on a fresh window should be allowed
    r2 = client.post('/api/auth/login', json={'username': 'admin', 'password': 'wrong'})
    assert r2.status_code == 401  # 401 not 429


def test_locked_ip_message_contains_retry_info():
    for _ in range(MAX_ATTEMPTS):
        client.post('/api/auth/login', json={'username': 'x', 'password': 'x'})
    r = client.post('/api/auth/login', json={'username': 'x', 'password': 'x'})
    assert r.status_code == 429
    detail = r.json().get('detail', '')
    assert 'seconds' in detail.lower() or 'wait' in detail.lower() or 'انتظر' in detail
