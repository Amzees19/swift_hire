"""
User CRUD and activation/deactivation helpers.
"""
from __future__ import annotations

import secrets
from datetime import datetime
from typing import Dict, Optional

from core.db.base import get_conn
from core.db.users.auth import hash_password

try:
    import psycopg
except Exception:  # pragma: no cover - optional in SQLite-only mode
    psycopg = None

def create_user(email: str, raw_password: str, role: str = "user", verified: bool = True) -> int:
    conn = get_conn()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat(timespec="seconds")

    password_hash = hash_password(raw_password)
    email_verified_at = now if verified else None

    cur.execute(
        """
        INSERT INTO users (email, password_hash, role, created_at, email_verified_at)
        VALUES (?, ?, ?, ?, ?)
        RETURNING id
        """,
        (email.strip().lower(), password_hash, role, now, email_verified_at),
    )
    row = cur.fetchone()
    user_id = int(row["id"]) if row else 0

    conn.commit()
    conn.close()
    return user_id


def get_user_by_email(email: str) -> Dict | None:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, email, password_hash, role, active, created_at, email_verified_at
        FROM users
        WHERE email = ?
        """,
        (email.strip().lower(),),
    )
    row = cur.fetchone()
    conn.close()

    return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[Dict]:
    """Look up a user by numeric id. Returns dict or None."""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, email, password_hash, role, active, created_at, email_verified_at
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    )
    row = cur.fetchone()
    conn.close()

    return dict(row) if row else None


def update_user_password(user_id: int, raw_password: str) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET password_hash=? WHERE id=?",
        (hash_password(raw_password), user_id),
    )
    conn.commit()
    conn.close()


def deactivate_user(user_id: int) -> None:
    """Deactivate a user and all their subscriptions."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT email FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    email = row["email"] if row else None
    now = datetime.utcnow().isoformat(timespec="seconds")

    cur.execute("UPDATE users SET active=0 WHERE id=?", (user_id,))
    if email:
        cur.execute(
            """
            UPDATE subscriptions
            SET active=0,
                last_deactivated_at=?,
                needs_pref_update=0
            WHERE user_id=? OR email=?
            """,
            (now, user_id, email),
        )
    conn.commit()
    conn.close()


def reactivate_user(user_id: int) -> None:
    """
    Reactivate a user and ONLY their most recently deactivated subscription.
    Also mark that subscription as needing a preference update and log an activation event.
    """

    def _generate_activation_code(cur, user_id: int, sub_id: int, now: str) -> None:
        """
        Insert an activation event with a short, random code (<=10 chars).
        Retries on rare collisions against the UNIQUE activation_code column.
        """
        for _ in range(5):
            code = secrets.token_urlsafe(8)[:10]
            try:
                cur.execute(
                    """
                    INSERT INTO activation_events (activation_code, user_id, subscription_id, activated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (code, user_id, sub_id, now),
                )
                return
            except Exception as exc:
                if psycopg and isinstance(exc, psycopg.errors.UniqueViolation):
                    continue
                raise
        raise RuntimeError("Failed to generate unique activation_code after retries")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT email FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    email = row["email"] if row else None
    now = datetime.utcnow().isoformat(timespec="seconds")

    cur.execute("UPDATE users SET active=1 WHERE id=?", (user_id,))
    if email:
        cur.execute(
            """
            SELECT id FROM subscriptions
            WHERE email = ? AND active = 0
            ORDER BY last_deactivated_at DESC, id DESC
            LIMIT 1
            """,
            (email,),
        )
        row = cur.fetchone()
        if row:
            sub_id = row["id"]
            cur.execute(
                """
                UPDATE subscriptions
                SET active=1,
                    needs_pref_update=1
                WHERE id=?
                """,
                (sub_id,),
            )
            _generate_activation_code(cur, user_id, sub_id, now)

    conn.commit()
    conn.close()


def delete_user_data(user_id: int) -> None:
    """
    Remove a user and related data: sessions, tokens, subscriptions, user row.
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT email FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    email = row["email"] if row else None

    try:
        cur.execute("DELETE FROM alert_deliveries WHERE user_id=?", (user_id,))
    except Exception:
        pass

    cur.execute("DELETE FROM password_reset_tokens WHERE user_id=?", (user_id,))
    try:
        cur.execute("DELETE FROM email_verification_tokens WHERE user_id=?", (user_id,))
    except Exception:
        pass
    cur.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
    if email:
        cur.execute("DELETE FROM subscriptions WHERE user_id=? OR lower(email)=lower(?)", (user_id, email))
        try:
            cur.execute("DELETE FROM activation_events WHERE user_id=?", (user_id,))
        except Exception:
            pass
    cur.execute("DELETE FROM users WHERE id=?", (user_id,))

    conn.commit()
    conn.close()


def get_deleted_users(limit: int = 100):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, user_id, email, role, created_at, deleted_at
            FROM deleted_users
            ORDER BY deleted_at DESC, id DESC
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
    "create_user",
    "get_user_by_email",
    "get_user_by_id",
    "update_user_password",
    "deactivate_user",
    "reactivate_user",
    "delete_user_data",
    "get_deleted_users",
]
