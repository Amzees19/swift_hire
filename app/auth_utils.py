"""
Helpers for session cookies and current-user lookup.
"""
from __future__ import annotations

import os

from fastapi import Request
from fastapi.responses import Response

from core.database import delete_session, get_session, get_user_by_id, touch_session

SESSION_COOKIE_NAME = "session_id"
SESSION_COOKIE_MAX_AGE = 1800  # 30 minutes
SECURE_COOKIES = (
    os.getenv("COOKIE_SECURE", "").lower() in ("1", "true", "yes")
    or os.getenv("PUBLIC_BASE_URL", "").lower().startswith("https://")
)


def get_current_user(request: Request):
    """
    Read session cookie and return (user_dict, session_token) or (None, None).
    Refreshes inactivity timeout when the session is valid.
    """
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None, None

    session = get_session(token)
    if not session:
        return None, token

    user = get_user_by_id(session["user_id"])
    if not user:
        delete_session(token)
        return None, token

    # Block unverified users from having an active session
    if user.get("email_verified_at") in (None, ""):
        delete_session(token)
        return None, token

    touch_session(token)
    return user, token


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=SESSION_COOKIE_MAX_AGE,
        samesite="lax",
        secure=SECURE_COOKIES,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME)
