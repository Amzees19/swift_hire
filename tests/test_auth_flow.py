import pytest
from fastapi.testclient import TestClient

import app.api as api_module
from app.routes import auth, public, dashboard


def test_login_logout_flow_redirects_when_user_missing(monkeypatch):
    client = TestClient(api_module.app)

    # Stub auth helpers
    monkeypatch.setattr(auth, "allow_request_with_remaining", lambda *a, **k: (True, 9))
    monkeypatch.setattr(auth, "validate_csrf", lambda req, tok: True)
    monkeypatch.setattr(auth, "get_user_by_email", lambda email: {"id": 1, "password_hash": "x", "email_verified_at": "2025-01-01T00:00:00"})
    monkeypatch.setattr(auth, "verify_password", lambda pw, hash_: True)
    monkeypatch.setattr(auth, "create_session", lambda uid: "session-token")
    # Avoid DB side effects
    monkeypatch.setattr(auth, "set_session_cookie", lambda resp, token: resp.set_cookie("session_id", token))

    resp = client.post(
        "/login",
        data={"email": "user@example.com", "password": "Passw0rd1", "csrf_token": "ok"},
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303)
    assert "session_id" in resp.cookies

    # Simulate missing/invalid session for protected route
    monkeypatch.setattr(dashboard, "get_current_user", lambda req: (None, None))
    resp2 = client.get("/dashboard", follow_redirects=False)
    assert resp2.status_code in (302, 303)
    assert "/login" in resp2.headers.get("location", "")


def test_subscribe_rate_limit_integration(monkeypatch):
    client = TestClient(api_module.app)

    # Force rate limit fail and bypass CSRF/validation
    monkeypatch.setattr(public, "allow_request", lambda *a, **k: False)
    monkeypatch.setattr(public, "validate_csrf", lambda req, tok: True)
    monkeypatch.setattr(public, "_is_valid_email", lambda e: True)
    monkeypatch.setattr(public, "_is_valid_password", lambda p: True)
    monkeypatch.setattr(public, "get_user_by_email", lambda e: None)
    monkeypatch.setattr(public, "create_user", lambda e, p: 1)
    monkeypatch.setattr(public, "verify_password", lambda pw, h: True)
    monkeypatch.setattr(public, "reactivate_user", lambda uid: None)
    monkeypatch.setattr(public, "add_subscription", lambda *a, **k: None)
    monkeypatch.setattr(public, "create_session", lambda uid: "session-token")
    monkeypatch.setattr(public, "set_session_cookie", lambda resp, token: resp.set_cookie("session_id", token))

    resp = client.post(
        "/subscribe",
        data={
            "email": "user@example.com",
            "password": "Passw0rd1",
            "password2": "Passw0rd1",
            "preferred_location1": "Any",
            "preferred_location2": "",
            "preferred_location3": "",
            "job_type": "Any",
            "csrf_token": "ok",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 429
