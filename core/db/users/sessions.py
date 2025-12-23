"""
Session storage helpers.
"""
from __future__ import annotations

import secrets
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Optional

from core.db.base import database_path

SESSION_TIMEOUT_MINUTES = 30  # inactivity timeout


def create_session(user_id: int) -> str:
    """Create a new login session for the given user_id and return the session token."""
    token = secrets.token_urlsafe(32)
    now = datetime.utcnow()
    expires = now + timedelta(minutes=SESSION_TIMEOUT_MINUTES)

    conn = sqlite3.connect(database_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO sessions (id, user_id, created_at, last_seen_at, expires_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            token,
            user_id,
            now.isoformat(timespec="seconds"),
            now.isoformat(timespec="seconds"),
            expires.isoformat(timespec="seconds"),
        ),
    )
    conn.commit()
    conn.close()

    return token


def delete_session(session_id: str) -> None:
    """Remove a session from the DB (logout)."""
    if not session_id:
        return

    conn = sqlite3.connect(database_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()


def get_session(session_id: str) -> Optional[Dict]:
    """
    Look up a session by id.
    - Returns None if it does not exist or has expired.
    - If expired, it is removed from the DB.
    """
    if not session_id:
        return None

    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, user_id, created_at, last_seen_at, expires_at
        FROM sessions
        WHERE id = ?
        """,
        (session_id,),
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    expires_at_str = row["expires_at"]
    try:
        expires_at = datetime.fromisoformat(expires_at_str)
    except Exception:
        delete_session(session_id)
        return None

    if expires_at < datetime.utcnow():
        delete_session(session_id)
        return None

    return dict(row)


def touch_session(session_id: str) -> None:
    """Extend a session's expiry based on current time (sliding window)."""
    if not session_id:
        return

    now = datetime.utcnow()
    new_expires = now + timedelta(minutes=SESSION_TIMEOUT_MINUTES)

    conn = sqlite3.connect(database_path)
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE sessions
        SET last_seen_at = ?, expires_at = ?
        WHERE id = ?
        """,
        (
            now.isoformat(timespec="seconds"),
            new_expires.isoformat(timespec="seconds"),
            session_id,
        ),
    )
    conn.commit()
    conn.close()


__all__ = [
    "SESSION_TIMEOUT_MINUTES",
    "create_session",
    "delete_session",
    "get_session",
    "touch_session",
]
