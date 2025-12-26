from core.db.base import get_conn
from core.db.users import user_store


def _seed_user_sub_job():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO users (email, password_hash, role, active, created_at, email_verified_at)
        VALUES (?, ?, 'user', 1, ?, ?)
        RETURNING id
        """,
        ("user@example.com", "x", "2020-01-01T00:00:00", "2020-01-01T00:00:00"),
    )
    user_id = int(cur.fetchone()["id"])

    cur.execute(
        """
        INSERT INTO subscriptions (user_id, email, preferred_location, job_type, created_at, active)
        VALUES (?, ?, ?, ?, ?, 1)
        RETURNING id
        """,
        (user_id, "USER@EXAMPLE.COM", "London", "Any", "2020-01-01T00:00:00"),
    )
    sub_id = int(cur.fetchone()["id"])

    cur.execute(
        """
        INSERT INTO jobs (title, location, url)
        VALUES (?, ?, ?)
        RETURNING id
        """,
        ("J", "L", "U"),
    )
    job_id = int(cur.fetchone()["id"])

    cur.execute(
        """
        INSERT INTO alert_deliveries (user_id, subscription_id, job_id, status, created_at)
        VALUES (?, ?, ?, 'queued', ?)
        """,
        (user_id, sub_id, job_id, "2020-01-01T00:00:00"),
    )

    conn.commit()
    conn.close()
    return user_id


def _count(table: str) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) AS count FROM {table}")
    count = int(cur.fetchone()["count"])
    conn.close()
    return count


def test_delete_user_data_removes_subscriptions_case_insensitive():
    user_id = _seed_user_sub_job()

    assert _count("subscriptions") == 1
    assert _count("alert_deliveries") == 1

    user_store.delete_user_data(user_id)

    assert _count("subscriptions") == 0
    assert _count("alert_deliveries") == 0
    assert _count("users") == 0
