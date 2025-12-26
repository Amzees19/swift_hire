"""
Password reset token storage.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Optional

from core.db.base import get_conn

RESET_TOKEN_MINUTES = 60


def create_password_reset_token(user_id: int) -> str:
    import secrets

    token = secrets.token_urlsafe(32)
    now = datetime.utcnow()
    expires = now + timedelta(minutes=RESET_TOKEN_MINUTES)

    conn = get_conn()
    cur = conn.cursor()
    # Invalidate any existing tokens for this user
    cur.execute("DELETE FROM password_reset_tokens WHERE user_id = ?", (user_id,))
    cur.execute(
        """
        INSERT INTO password_reset_tokens (user_id, token, created_at, expires_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            user_id,
            token,
            now.isoformat(timespec="seconds"),
            expires.isoformat(timespec="seconds"),
        ),
    )
    conn.commit()
    conn.close()
    return token


def get_password_reset_token(token: str) -> Optional[Dict]:
    if not token:
        return None

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, user_id, token, created_at, expires_at, used_at
        FROM password_reset_tokens
        WHERE token = ?
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
        cur.execute("DELETE FROM password_reset_tokens WHERE token = ?", (token,))
        conn.commit()
        conn.close()
        return None

    if data.get("used_at") or expires_at < datetime.utcnow():
        cur.execute("DELETE FROM password_reset_tokens WHERE token = ?", (token,))
        conn.commit()
        conn.close()
        return None

    conn.close()
    return data


def mark_reset_token_used(token: str) -> None:
    if not token:
        return
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM password_reset_tokens WHERE token = ?", (token,))
    row = cur.fetchone()
    if not row:
        user_id = None
    elif isinstance(row, dict):
        user_id = row.get("user_id")
    else:
        user_id = row[0]
    cur.execute(
        "UPDATE password_reset_tokens SET used_at=? WHERE token=?",
        (datetime.utcnow().isoformat(timespec="seconds"), token),
    )
    if user_id:
        cur.execute("DELETE FROM password_reset_tokens WHERE user_id = ? AND token != ?", (user_id, token))
    conn.commit()
    conn.close()


__all__ = [
    "RESET_TOKEN_MINUTES",
    "create_password_reset_token",
    "get_password_reset_token",
    "mark_reset_token_used",
]
