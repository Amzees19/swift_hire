import types

import pytest

from app import security
from app.routes import admin
from app.routes import auth
from app.routes import public


def test_csrf_validation_success_and_failure():
    class DummyReq:
        def __init__(self, cookies):
            self.cookies = cookies

    token = security.issue_csrf_token()
    req_ok = DummyReq({security.CSRF_COOKIE_NAME: token})
    assert security.validate_csrf(req_ok, token) is True

    req_bad = DummyReq({security.CSRF_COOKIE_NAME: token})
    assert security.validate_csrf(req_bad, "wrong") is False
    req_missing = DummyReq({})
    assert security.validate_csrf(req_missing, token) is False


def test_rate_limit_sliding_window():
    key = "test:rl"
    allowed, remaining = security.allow_request_with_remaining(key, limit=2, window_seconds=60)
    assert allowed is True and remaining == 1
    allowed, remaining = security.allow_request_with_remaining(key, limit=2, window_seconds=60)
    assert allowed is True and remaining == 0
    allowed, remaining = security.allow_request_with_remaining(key, limit=2, window_seconds=60)
    assert allowed is False and remaining == 0


def test_admin_route_forbidden_for_non_admin(monkeypatch):
    # Stub get_current_user to return a normal user
    monkeypatch.setattr(admin, "get_current_user", lambda req: ({"role": "user"}, None))
    # Avoid hitting the real DB
    monkeypatch.setattr(admin, "get_all_jobs", lambda limit=100: [])

    class DummyReq:
        pass

    resp = admin.list_jobs(DummyReq())
    assert resp.status_code == 403


def test_admin_route_redirect_when_not_logged_in(monkeypatch):
    monkeypatch.setattr(admin, "get_current_user", lambda req: (None, None))
    monkeypatch.setattr(admin, "get_all_jobs", lambda limit=100: [])

    class DummyReq:
        pass

    resp = admin.list_jobs(DummyReq())
    assert resp.status_code in (302, 303)


def test_login_rejects_missing_csrf(monkeypatch):
    # Allow rate limit to pass
    monkeypatch.setattr(auth, "allow_request_with_remaining", lambda *a, **k: (True, 9))
    dummy_req = types.SimpleNamespace(
        client=types.SimpleNamespace(host="127.0.0.1"),
        cookies={security.CSRF_COOKIE_NAME: "cookie-token"},
    )
    resp = auth.login(dummy_req, email="user@example.com", password="bad", csrf_token="wrong")
    assert resp.status_code == 403


def test_password_reset_rejects_missing_csrf(monkeypatch):
    monkeypatch.setattr(auth, "allow_request_with_remaining", lambda *a, **k: (True, 5))
    dummy_req = types.SimpleNamespace(
        client=types.SimpleNamespace(host="127.0.0.1"),
        cookies={security.CSRF_COOKIE_NAME: "cookie-token"},
    )
    resp = auth.password_reset_request(dummy_req, email="user@example.com", csrf_token="wrong")
    assert resp.status_code == 403


def test_subscribe_rejects_missing_csrf(monkeypatch):
    # Bypass rate limit and DB calls by stubbing
    monkeypatch.setattr(public, "allow_request", lambda *a, **k: True)
    dummy_req = types.SimpleNamespace(
        client=types.SimpleNamespace(host="127.0.0.1"),
        cookies={security.CSRF_COOKIE_NAME: "cookie-token"},
    )
    resp = public.subscribe(
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
    assert resp.status_code == 403


def test_admin_subscriptions_forbidden_for_non_admin(monkeypatch):
    monkeypatch.setattr(admin, "get_current_user", lambda req: ({"role": "user"}, None))
    monkeypatch.setattr(admin, "get_active_subscriptions", lambda: [])

    class DummyReq:
        pass

    resp = admin.list_subscriptions(DummyReq())
    assert resp.status_code == 403
