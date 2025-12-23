"""
Lightweight CSRF + rate limit helpers.
"""
from __future__ import annotations

import hmac
import os
import secrets
import time
from typing import Dict

CSRF_COOKIE_NAME = "csrf_token"
SECURE_COOKIES = (
    os.getenv("COOKIE_SECURE", "").lower() in ("1", "true", "yes")
    or os.getenv("PUBLIC_BASE_URL", "").lower().startswith("https://")
)


def issue_csrf_token(existing: str | None = None) -> str:
    """Return a CSRF token (re-use existing if provided, else create a new one)."""
    return existing or secrets.token_urlsafe(16)


def attach_csrf_cookie(response, token: str) -> None:
    """
    Attach the CSRF token as a non-HTTPOnly cookie (double-submit pattern).
    Uses samesite=lax and no secure flag (enable secure=True when on HTTPS).
    """
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        httponly=False,
        samesite="lax",
        secure=SECURE_COOKIES,
    )


def validate_csrf(request, form_token: str | None) -> bool:
    """Compare the submitted token with the cookie value using constant-time compare."""
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME) or ""
    form_token = form_token or ""
    if not cookie_token or not form_token:
        return False
    return hmac.compare_digest(cookie_token, form_token)


# -------- Rate limiting (in-memory) --------
_rate_state: Dict[str, list[float]] = {}


def allow_request(key: str, limit: int = 5, window_seconds: int = 60) -> bool:
    """
    Simple sliding-window rate limit stored in memory.
    Returns True if under limit, False otherwise.
    """
    allowed, _ = allow_request_with_remaining(key, limit=limit, window_seconds=window_seconds)
    return allowed


def allow_request_with_remaining(key: str, limit: int = 5, window_seconds: int = 60) -> (bool, int):
    """
    Sliding-window rate limit with remaining-count feedback.
    Returns (allowed: bool, remaining_after: int).
    """
    now = time.time()
    window_start = now - window_seconds
    history = _rate_state.get(key, [])
    history = [t for t in history if t > window_start]
    if len(history) >= limit:
        _rate_state[key] = history
        return False, 0
    history.append(now)
    _rate_state[key] = history
    remaining_after = max(0, limit - len(history))
    return True, remaining_after


__all__ = [
    "CSRF_COOKIE_NAME",
    "issue_csrf_token",
    "attach_csrf_cookie",
    "validate_csrf",
    "allow_request",
    "allow_request_with_remaining",
]
