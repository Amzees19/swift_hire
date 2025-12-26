from fastapi.testclient import TestClient

import app.api as api_module
from core.db.base import get_conn
from core.db.alerts.deliveries_store import create_alert_deliveries


def _seed_user_sub_job():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO users (email, password_hash, role, created_at)
        VALUES (?, ?, ?, ?)
        RETURNING id
        """,
        ("u@example.com", "x", "user", "2025-01-01T00:00:00"),
    )
    user_id = int(cur.fetchone()["id"])

    cur.execute(
        """
        INSERT INTO subscriptions (user_id, email, preferred_location, job_type, created_at, active)
        VALUES (?, ?, ?, ?, ?, 1)
        RETURNING id
        """,
        (user_id, "u@example.com", "Any", "Any", "2025-01-01T00:00:00"),
    )
    sub_id = int(cur.fetchone()["id"])

    cur.execute(
        """
        INSERT INTO jobs (title, type, duration, pay, location, url, first_seen_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        RETURNING id
        """,
        ("Job", "Full Time", "Regular", "1", "Rochester, NY", "http://x", "2025-01-01T00:00:00"),
    )
    job_id = int(cur.fetchone()["id"])

    conn.commit()
    conn.close()
    return user_id, sub_id, job_id


def test_my_alerts_shows_only_user_history(monkeypatch):
    user_id, sub_id, job_id = _seed_user_sub_job()

    create_alert_deliveries(user_id=user_id, subscription_id=sub_id, job_ids=[job_id])

    import app.routes.my_alerts as my_alerts_route
    monkeypatch.setattr(
        my_alerts_route,
        "get_current_user",
        lambda request: ({"id": user_id, "email": "u@example.com"}, "tok"),
    )

    client = TestClient(api_module.app)
    resp = client.get("/my-alerts")
    assert resp.status_code == 200
    assert "Job" in resp.text
    assert "Rochester" in resp.text
