"""
Jobs and locations storage helpers.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

from core.db.base import database_path


def get_locations() -> List[Dict]:
    """Return all active locations."""
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, code, name, region, country, active
        FROM locations
        WHERE active = 1
        ORDER BY name
        """
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_jobs(limit: Optional[int] = None) -> List[Dict]:
    """Return all stored jobs as a list of dicts, newest first."""
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    sql = """
        SELECT id, title, type, duration, pay, location, url, first_seen_at
        FROM jobs
        ORDER BY datetime(first_seen_at) DESC, id DESC
    """
    if limit is not None:
        sql += " LIMIT ?"
        cur.execute(sql, (limit,))
    else:
        cur.execute(sql)

    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_new_jobs(jobs: List[Dict]) -> List[Dict]:
    """
    Insert jobs into DB if they don't already exist.
    Returns a list of jobs that were newly inserted.
    """
    if not jobs:
        return []

    conn = sqlite3.connect(database_path)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM jobs")
    before_count = cur.fetchone()[0]

    new_jobs: List[Dict] = []
    now = datetime.utcnow().isoformat(timespec="seconds")

    for job in jobs:
        title = job.get("title") or ""
        location = job.get("location") or ""
        url = job.get("url") or ""

        try:
            cur.execute(
                """
                INSERT INTO jobs (title, type, duration, pay, location, url, first_seen_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    job.get("type"),
                    job.get("duration"),
                    job.get("pay"),
                    location,
                    url,
                    now,
                ),
            )
            # Attach DB-generated identity so callers (worker, alert history) can link reliably.
            job_with_id = dict(job)
            job_with_id["id"] = cur.lastrowid
            job_with_id["first_seen_at"] = now
            new_jobs.append(job_with_id)
        except sqlite3.IntegrityError:
            continue

    conn.commit()

    cur.execute("SELECT COUNT(*) FROM jobs")
    after_count = cur.fetchone()[0]
    conn.close()

    print(
        f"[db] get_new_jobs: before={before_count}, inserted={len(new_jobs)}, "
        f"after={after_count}, db={database_path.resolve()}"
    )

    return new_jobs


def get_stats() -> Dict:
    """Return simple stats about the database."""
    conn = sqlite3.connect(database_path)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM jobs")
    jobs_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM subscriptions WHERE active = 1")
    subs_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM locations WHERE active = 1")
    locs_count = cur.fetchone()[0]

    conn.close()

    return {
        "jobs": jobs_count,
        "active_subscriptions": subs_count,
        "locations": locs_count,
    }


__all__ = [
    "get_locations",
    "get_all_jobs",
    "get_new_jobs",
    "get_stats",
]
