"""
Email verification token storage helpers.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Optional

from core.db.base import database_path

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

    conn = sqlite3.connect(database_path)
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

    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Opportunistic cleanup of expired tokens
    cur.execute(
        "DELETE FROM email_verification_tokens WHERE used_at IS NULL AND datetime(expires_at) <= datetime('now')"
    )

    cur.execute(
        """
        SELECT id, user_id, token, created_at, expires_at, used_at
        FROM email_verification_tokens
        WHERE token = ? AND used_at IS NULL AND datetime(expires_at) > datetime('now')
        """,
        (token,),
    )
    row = cur.fetchone()
    conn.commit()
    conn.close()
    return dict(row) if row else None


def mark_email_verification_token_used(token: str) -> None:
    """Mark a token as used."""
    if not token:
        return
    conn = sqlite3.connect(database_path)
    cur = conn.cursor()
    cur.execute(
        "UPDATE email_verification_tokens SET used_at = datetime('now') WHERE token = ? AND used_at IS NULL",
        (token,),
    )
    conn.commit()
    conn.close()


def mark_user_email_verified(user_id: int) -> None:
    """Set email_verified_at if not already set."""
    conn = sqlite3.connect(database_path)
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET email_verified_at = datetime('now') WHERE id = ? AND (email_verified_at IS NULL OR email_verified_at = '')",
        (user_id,),
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

