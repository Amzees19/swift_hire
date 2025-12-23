from fastapi.testclient import TestClient

import app.api as api_module
from app.routes import auth


def test_verify_email_happy_path(monkeypatch):
    client = TestClient(api_module.app)

    monkeypatch.setattr(auth, "get_email_verification_token", lambda tok: {"user_id": 1} if tok == "t" else None)
    monkeypatch.setattr(auth, "get_user_by_id", lambda uid: {"id": uid, "email": "u@example.com", "role": "user"})
    monkeypatch.setattr(auth, "mark_user_email_verified", lambda uid: None)
    monkeypatch.setattr(auth, "mark_email_verification_token_used", lambda tok: None)
    monkeypatch.setattr(auth, "activate_latest_inactive_subscription", lambda email: True)
    monkeypatch.setattr(auth, "create_session", lambda uid: "session-token")
    monkeypatch.setattr(auth, "set_session_cookie", lambda resp, token: resp.set_cookie("session_id", token))

    resp = client.get("/verify-email?token=t", follow_redirects=False)
    assert resp.status_code in (302, 303)
    assert resp.headers.get("location") == "/dashboard"


def test_verify_email_invalid_token(monkeypatch):
    client = TestClient(api_module.app)
    monkeypatch.setattr(auth, "get_email_verification_token", lambda tok: None)
    resp = client.get("/verify-email?token=bad")
    assert resp.status_code == 200
    assert "invalid or expired" in resp.text.lower()

