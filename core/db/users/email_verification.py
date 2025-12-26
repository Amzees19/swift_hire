"""
Email verification token storage helpers.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Optional

from core.db.base import get_conn

VERIFY_TOKEN_HOURS = 24


def create_email_verification_token(user_id: int) -> str:
    """
    Create a new single-use email verification token for a user.
    """
    import secrets

    token = secrets.token_urlsafe(32)
    now = datetime.utcnow()
    created_at = now.isoformat(timespec="seconds")
    expires_at = (now + timedelta(hours=VERIFY_TOKEN_HOURS)).isoformat(timespec="seconds")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO email_verification_tokens (user_id, token, created_at, expires_at, used_at)
        VALUES (?, ?, ?, ?, NULL)
        """,
        (user_id, token, created_at, expires_at),
    )
    conn.commit()
    conn.close()
    return token


def get_email_verification_token(token: str) -> Optional[Dict]:
    """
    Return the token row if valid (not used, not expired). Otherwise return None.
    """
    if not token:
        return None

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, user_id, token, created_at, expires_at, used_at
        FROM email_verification_tokens
        WHERE token = ? AND used_at IS NULL
        """,
        (token,),
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        return None

    data = dict(row)
    try:
        expires_at = datetime.fromisoformat(data["expires_at"])
    except Exception:
        cur.execute("DELETE FROM email_verification_tokens WHERE token = ?", (token,))
        conn.commit()
        conn.close()
        return None

    if expires_at <= datetime.utcnow():
        cur.execute("DELETE FROM email_verification_tokens WHERE token = ?", (token,))
        conn.commit()
        conn.close()
        return None

    conn.close()
    return data


def mark_email_verification_token_used(token: str) -> None:
    """Mark a token as used."""
    if not token:
        return
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE email_verification_tokens SET used_at = ? WHERE token = ? AND used_at IS NULL",
        (datetime.utcnow().isoformat(timespec="seconds"), token),
    )
    conn.commit()
    conn.close()


def mark_user_email_verified(user_id: int) -> None:
    """Set email_verified_at if not already set."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET email_verified_at = ? WHERE id = ? AND (email_verified_at IS NULL OR email_verified_at = '')",
        (datetime.utcnow().isoformat(timespec="seconds"), user_id),
    )
    conn.commit()
    conn.close()


__all__ = [
    "VERIFY_TOKEN_HOURS",
    "create_email_verification_token",
    "get_email_verification_token",
    "mark_email_verification_token_used",
    "mark_user_email_verified",
]
