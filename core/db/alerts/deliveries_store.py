"""
Alert delivery history store.

This records which jobs were matched for a specific subscription/user, and whether an email was sent.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Dict, Iterable, List, Optional

from core.db.base import get_conn


def create_alert_deliveries(
    *,
    user_id: int,
    subscription_id: int,
    job_ids: Iterable[int],
) -> List[int]:
    """
    Insert delivery rows for (subscription_id, job_id) if missing.

    Returns the list of job_ids that were newly inserted (best-effort).
    """
    job_ids_list = [int(j) for j in job_ids if j is not None]
    if not job_ids_list:
        return []

    now = datetime.utcnow().isoformat(timespec="seconds")
    inserted: List[int] = []

    conn = get_conn()
    cur = conn.cursor()
    for job_id in job_ids_list:
        try:
            cur.execute(
                """
                INSERT OR IGNORE INTO alert_deliveries
                  (user_id, subscription_id, job_id, status, created_at, sent_at, error)
                VALUES (?, ?, ?, 'queued', ?, NULL, NULL)
                """,
                (user_id, subscription_id, job_id, now),
            )
            if cur.rowcount:
                inserted.append(job_id)
        except sqlite3.OperationalError:
            # If table doesn't exist yet for some reason, don't crash callers.
            continue

    conn.commit()
    conn.close()
    return inserted


def mark_alert_deliveries_sent(*, subscription_id: int, job_ids: Iterable[int]) -> None:
    job_ids_list = [int(j) for j in job_ids if j is not None]
    if not job_ids_list:
        return

    now = datetime.utcnow().isoformat(timespec="seconds")
    conn = get_conn()
    cur = conn.cursor()

    for job_id in job_ids_list:
        cur.execute(
            """
            UPDATE alert_deliveries
            SET status='sent', sent_at=?, error=NULL
            WHERE subscription_id=? AND job_id=?
            """,
            (now, subscription_id, job_id),
        )

    conn.commit()
    conn.close()


def mark_alert_deliveries_failed(*, subscription_id: int, job_ids: Iterable[int], error: str) -> None:
    job_ids_list = [int(j) for j in job_ids if j is not None]
    if not job_ids_list:
        return

    now = datetime.utcnow().isoformat(timespec="seconds")
    conn = get_conn()
    cur = conn.cursor()

    for job_id in job_ids_list:
        cur.execute(
            """
            UPDATE alert_deliveries
            SET status='failed', sent_at=NULL, error=?, created_at=created_at
            WHERE subscription_id=? AND job_id=?
            """,
            (f"{error}".strip()[:500], subscription_id, job_id),
        )

    conn.commit()
    conn.close()


def get_alert_deliveries_for_user(*, user_id: int, limit: int = 200) -> List[Dict]:
    """
    Return delivery history joined with job fields, newest first.
    """
    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT
              ad.id AS delivery_id,
              ad.subscription_id,
              ad.status,
              ad.created_at AS delivery_created_at,
              ad.sent_at,
              ad.error,
              j.id AS job_id,
              j.title,
              j.location,
              j.type,
              j.duration,
              j.pay,
              j.url,
              j.first_seen_at
            FROM alert_deliveries ad
            JOIN jobs j ON j.id = ad.job_id
            WHERE ad.user_id = ?
            ORDER BY datetime(ad.created_at) DESC, ad.id DESC
            LIMIT ?
            """,
            (user_id, int(limit)),
        )
    except sqlite3.OperationalError:
        conn.close()
        return []

    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_alert_deliveries_for_user(user_id: int) -> None:
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM alert_deliveries WHERE user_id=?", (user_id,))
        conn.commit()
    except sqlite3.OperationalError:
        pass
    finally:
        conn.close()

