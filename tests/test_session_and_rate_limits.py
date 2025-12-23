import types

import pytest

from app import security
from app.routes import auth, admin, public
from app.auth_utils import get_current_user as real_get_current_user


def test_login_rate_limit(monkeypatch):
    # Force rate limit to deny after 1 attempt
    calls = {"count": 0}

    def fake_allow_request_with_remaining(key, limit=5, window_seconds=60):
        calls["count"] += 1
        allowed = calls["count"] < 2
        return allowed, (1 if allowed else 0)

    monkeypatch.setattr(auth, "allow_request_with_remaining", fake_allow_request_with_remaining)
    dummy_req = types.SimpleNamespace(
        client=types.SimpleNamespace(host="127.0.0.1"),
        cookies={security.CSRF_COOKIE_NAME: "cookie-token"},
    )

    # first call passes limit check but fails CSRF -> 403
    resp1 = auth.login(dummy_req, email="user@example.com", password="bad", csrf_token="wrong")
    # second call exceeds limit -> 429
    resp2 = auth.login(dummy_req, email="user@example.com", password="bad", csrf_token="wrong")
    assert resp2.status_code == 429


def test_subscribe_rate_limit(monkeypatch):
    calls = {"count": 0}

    def fake_allow_request(key, limit=5, window_seconds=60):
        calls["count"] += 1
        return calls["count"] < 2

    monkeypatch.setattr(public, "allow_request", fake_allow_request)
    dummy_req = types.SimpleNamespace(
        client=types.SimpleNamespace(host="127.0.0.1"),
        cookies={security.CSRF_COOKIE_NAME: "cookie-token"},
    )

    resp1 = public.subscribe(
        email="user@example.com",
        password="Passw0rd1",
        password2="Passw0rd1",
        preferred_location1="Any",
        preferred_location2="",
        preferred_location3="",
        job_type="Any",
        csrf_token="wrong",  # will fail CSRF, but we just want rate-limit path exercised
        request=dummy_req,
    )
    resp2 = public.subscribe(
        email="user@example.com",
        password="Passw0rd1",
        password2="Passw0rd1",
        preferred_location1="Any",
        preferred_location2="",
        preferred_location3="",
        job_type="Any",
        csrf_token="wrong",
        request=dummy_req,
    )
    assert resp2.status_code == 429


def test_session_cleared_for_missing_user(monkeypatch):
    # Simulate get_current_user returning (None, None)
    monkeypatch.setattr(auth, "get_current_user", lambda req: (None, None))

    class DummyReq:
        cookies = {}
        client = types.SimpleNamespace(host="127.0.0.1")

    resp = auth.logout(DummyReq())
    # Should redirect to home when session is gone
    assert resp.status_code in (302, 303)
