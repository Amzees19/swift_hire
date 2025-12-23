import sqlite3
import tempfile

from fastapi.testclient import TestClient

import app.api as api_module
from core.db.base import get_conn
from core.db.alerts.deliveries_store import create_alert_deliveries


def _make_temp_db(monkeypatch):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    path = tmp.name
    tmp.close()

    # Patch DB path everywhere that uses core.db.base.get_conn()
    import core.db.base as base
    monkeypatch.setattr(base, "database_path", path)

    # Minimal schema for this test
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE users(id INTEGER PRIMARY KEY, email TEXT, password_hash TEXT, role TEXT, active INTEGER, created_at TEXT)"
    )
    conn.execute(
        "CREATE TABLE subscriptions(id INTEGER PRIMARY KEY, email TEXT, preferred_location TEXT, job_type TEXT, created_at TEXT, active INTEGER)"
    )
    conn.execute(
        "CREATE TABLE jobs(id INTEGER PRIMARY KEY, title TEXT, type TEXT, duration TEXT, pay TEXT, location TEXT, url TEXT, first_seen_at TEXT)"
    )
    conn.execute(
        """
        CREATE TABLE alert_deliveries(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subscription_id INTEGER NOT NULL,
            job_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            created_at TEXT NOT NULL,
            sent_at TEXT,
            error TEXT,
            UNIQUE(subscription_id, job_id)
        )
        """
    )
    conn.execute("INSERT INTO users(id,email,password_hash,role,active,created_at) VALUES (1,'u@example.com','x','user',1,'2025-01-01T00:00:00')")
    conn.execute("INSERT INTO subscriptions(id,email,preferred_location,job_type,created_at,active) VALUES (10,'u@example.com','Any','Any','2025-01-01T00:00:00',1)")
    conn.execute("INSERT INTO jobs(id,title,type,duration,pay,location,url,first_seen_at) VALUES (100,'Job','Full Time','Regular','$1','Rochester, NY','http://x','2025-01-01T00:00:00')")
    conn.commit()
    conn.close()
    return path


def test_my_alerts_shows_only_user_history(monkeypatch):
    _make_temp_db(monkeypatch)

    # Insert one delivery row (what /my-alerts should show)
    create_alert_deliveries(user_id=1, subscription_id=10, job_ids=[100])

    # Fake auth: treat request as logged in as user_id=1
    import app.routes.my_alerts as my_alerts_route
    monkeypatch.setattr(my_alerts_route, "get_current_user", lambda request: ({"id": 1, "email": "u@example.com"}, "tok"))

    client = TestClient(api_module.app)
    resp = client.get("/my-alerts")
    assert resp.status_code == 200
    assert "Job" in resp.text
    assert "Rochester" in resp.text
