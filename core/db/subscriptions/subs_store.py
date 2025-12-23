"""
Subscription storage helpers (data-level only).
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Dict, List

from core.db.base import database_path


def add_subscription(
    email: str,
    preferred_location: str,
    job_type: str,
    active: int = 1,
    user_id: int | None = None,
) -> None:
    """Add a new subscription (active=1 by default)."""
    conn = sqlite3.connect(database_path)
    cur = conn.cursor()
    now = datetime.utcnow().isoformat(timespec="seconds")
    email_normalized = (email or "").strip().lower()

    cur.execute(
        """
        INSERT INTO subscriptions (user_id, email, preferred_location, job_type, created_at, active)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, email_normalized, preferred_location, job_type, now, int(active)),
    )

    conn.commit()
    conn.close()


def activate_latest_inactive_subscription(email: str) -> bool:
    """Activate the most recently created inactive subscription for an email."""
    email_normalized = (email or "").strip().lower()
    if not email_normalized:
        return False

    conn = sqlite3.connect(database_path)
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE subscriptions
        SET active = 1
        WHERE id = (
            SELECT id FROM subscriptions
            WHERE lower(email) = lower(?) AND active = 0
            ORDER BY datetime(created_at) DESC, id DESC
            LIMIT 1
        )
        """,
        (email_normalized,),
    )
    updated = cur.rowcount
    conn.commit()
    conn.close()
    return updated > 0


def get_active_subscriptions() -> List[Dict]:
    """Return all active subscriptions as a list of dicts."""
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, user_id, email, preferred_location, job_type
        FROM subscriptions
        WHERE active = 1
        """
    )

    rows = cur.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_subscriptions_for_email(email: str) -> List[Dict]:
    """Return all subscriptions for a given email."""
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, user_id, email, preferred_location, job_type, created_at, active, updated_once, needs_pref_update, last_deactivated_at
        FROM subscriptions
        WHERE lower(email) = lower(?)
        ORDER BY datetime(created_at) DESC, id DESC
        """,
        (email.strip(),),
    )

    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def deactivate_subscription(sub_id: int) -> None:
    """Mark a subscription as inactive (unsubscribe)."""
    conn = sqlite3.connect(database_path)
    cur = conn.cursor()

    cur.execute("UPDATE subscriptions SET active = 0 WHERE id = ?", (sub_id,))

    conn.commit()
    conn.close()


def update_subscription_for_user(sub_id: int, email: str, preferred_location: str, job_type: str) -> bool:
    """
    Update a subscription owned by email.
    - Enforce max 3 locations (semicolon separated).
    - Enforce max 3 locations (semicolon separated).
    - Allow updates any time for the owner.
    - After update, set updated_once=1, keep it active.
    Returns True if a row was updated.
    """
    parts = [p.strip() for p in preferred_location.split(";") if p.strip()]
    trimmed = "; ".join(parts[:3])

    conn = sqlite3.connect(database_path)
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE subscriptions
        SET preferred_location = ?, job_type = ?, updated_once = 1, needs_pref_update = 0, active = 1
        WHERE id = ? AND lower(email) = lower(?)
        """,
        (trimmed, job_type, sub_id, email.strip()),
    )
    updated = cur.rowcount
    conn.commit()
    conn.close()
    return updated > 0


def get_deleted_subscriptions(limit: int = 100) -> List[Dict]:
    """Return recently deleted subscriptions (archive view)."""
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, subscription_id, user_id, email, preferred_location, job_type, created_at, active, deleted_at
            FROM deleted_subscriptions
            ORDER BY datetime(deleted_at) DESC, id DESC
            LIMIT ?
            """,
            (int(limit),),
        )
        rows = cur.fetchall()
    except Exception:
        rows = []
    conn.close()
    return [dict(r) for r in rows]


__all__ = [
    "add_subscription",
    "activate_latest_inactive_subscription",
    "get_active_subscriptions",
    "get_subscriptions_for_email",
    "deactivate_subscription",
    "update_subscription_for_user",
    "get_deleted_subscriptions",
]
