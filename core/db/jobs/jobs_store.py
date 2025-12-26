"""
Jobs and locations storage helpers.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from core.db.base import get_conn


def get_locations() -> List[Dict]:
    """Return all active locations."""
    conn = get_conn()
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
    conn = get_conn()
    cur = conn.cursor()

    sql = """
        SELECT id, title, type, duration, pay, location, url, first_seen_at
        FROM jobs
        ORDER BY first_seen_at DESC, id DESC
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

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS count FROM jobs")
    before_row = cur.fetchone()
    before_count = before_row["count"] if before_row else 0

    new_jobs: List[Dict] = []
    now = datetime.utcnow().isoformat(timespec="seconds")

    for job in jobs:
        title = job.get("title") or ""
        location = job.get("location") or ""
        url = job.get("url") or ""

        cur.execute(
            """
            INSERT INTO jobs (title, type, duration, pay, location, url, first_seen_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (title, location, url) DO NOTHING
            RETURNING id
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
        row = cur.fetchone()
        if row:
            job_with_id = dict(job)
            job_with_id["id"] = row["id"]
            job_with_id["first_seen_at"] = now
            new_jobs.append(job_with_id)

    conn.commit()

    cur.execute("SELECT COUNT(*) AS count FROM jobs")
    after_row = cur.fetchone()
    after_count = after_row["count"] if after_row else 0
    conn.close()

    print(
        f"[db] get_new_jobs: before={before_count}, inserted={len(new_jobs)}, "
        f"after={after_count}, db=postgres"
    )

    return new_jobs


def get_stats() -> Dict:
    """Return simple stats about the database."""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS count FROM jobs")
    jobs_row = cur.fetchone()
    jobs_count = jobs_row["count"] if jobs_row else 0

    cur.execute("SELECT COUNT(*) AS count FROM subscriptions WHERE active = 1")
    subs_row = cur.fetchone()
    subs_count = subs_row["count"] if subs_row else 0

    cur.execute("SELECT COUNT(*) AS count FROM locations WHERE active = 1")
    locs_row = cur.fetchone()
    locs_count = locs_row["count"] if locs_row else 0

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
