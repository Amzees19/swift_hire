import pytest
from starlette.requests import Request
from starlette.responses import HTMLResponse

from app.routes import auth


def test_password_reset_confirm_invalid_token(monkeypatch):
    # Force rate limit allow and CSRF pass
    monkeypatch.setattr(auth, "allow_request", lambda *a, **k: True)
    monkeypatch.setattr(auth, "validate_csrf", lambda req, token: True)
    dummy_req = type("Req", (), {"client": type("C", (), {"host": "127.0.0.1"})(), "cookies": {}})

    resp = auth.password_reset_confirm(
        dummy_req,
        token="invalid",
        password="Passw0rd1",
        password2="Passw0rd1",
        csrf_token="ok",
    )
    assert isinstance(resp, HTMLResponse)
    assert resp.status_code == 200
    assert b"Reset link is invalid or expired." in resp.body


def test_password_reset_confirm_single_use(monkeypatch):
    # Dummy valid token data
    token_data = {"user_id": 42}
    monkeypatch.setattr(auth, "allow_request", lambda *a, **k: True)
    monkeypatch.setattr(auth, "validate_csrf", lambda req, token: True)
    monkeypatch.setattr(auth, "get_password_reset_token", lambda token: token_data if token == "valid" else None)

    actions = {"updated": False, "used": False}
    monkeypatch.setattr(auth, "get_user_by_id", lambda uid: {"id": uid, "role": "user"})
    monkeypatch.setattr(auth, "update_user_password", lambda uid, pw: actions.__setitem__("updated", True))
    monkeypatch.setattr(auth, "mark_reset_token_used", lambda tok: actions.__setitem__("used", True))

    dummy_req = type("Req", (), {"client": type("C", (), {"host": "127.0.0.1"})(), "cookies": {}})

    resp = auth.password_reset_confirm(
        dummy_req,
        token="valid",
        password="Passw0rd1",
        password2="Passw0rd1",
        csrf_token="ok",
    )
    assert resp.status_code == 200
    assert actions["updated"] is True
    assert actions["used"] is True

    # Second use should now fail because token lookup returns None
    monkeypatch.setattr(auth, "get_password_reset_token", lambda token: None)
    resp2 = auth.password_reset_confirm(
        dummy_req,
        token="valid",
        password="Passw0rd1",
        password2="Passw0rd1",
        csrf_token="ok",
    )
    assert b"Reset link is invalid or expired." in resp2.body
