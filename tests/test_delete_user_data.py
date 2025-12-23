import sqlite3
import tempfile

import pytest

from core.db.users import user_store


def _setup_db() -> str:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    conn = sqlite3.connect(tmp.name)
    conn.execute(
        """
        CREATE TABLE users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT,
            email_verified_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE subscriptions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            preferred_location TEXT,
            job_type TEXT,
            created_at TEXT,
            active INTEGER DEFAULT 1
        )
        """
    )
    conn.execute("CREATE TABLE sessions(id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, created_at TEXT, last_seen_at TEXT, expires_at TEXT)")
    conn.execute("CREATE TABLE password_reset_tokens(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, token TEXT, created_at TEXT, expires_at TEXT, used_at TEXT)")
    conn.execute("CREATE TABLE email_verification_tokens(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, token TEXT, created_at TEXT, expires_at TEXT, used_at TEXT)")
    conn.execute("CREATE TABLE activation_events(id INTEGER PRIMARY KEY AUTOINCREMENT, activation_code TEXT, user_id INTEGER, subscription_id INTEGER, activated_at TEXT)")
    conn.execute("CREATE TABLE jobs(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, location TEXT, url TEXT)")
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
    conn.commit()
    conn.close()
    return tmp.name


@pytest.fixture()
def temp_db(monkeypatch):
    path = _setup_db()
    monkeypatch.setattr(user_store, "database_path", path)
    return path


def test_delete_user_data_removes_subscriptions_case_insensitive(temp_db):
    conn = sqlite3.connect(temp_db)
    cur = conn.cursor()
    # user emails are stored normalized in app
    cur.execute("INSERT INTO users (email, password_hash, role, active, created_at, email_verified_at) VALUES ('user@example.com','x','user',1,'2020','2020')")
    user_id = cur.lastrowid
    # Insert subscription with different casing (legacy rows)
    cur.execute("INSERT INTO subscriptions (email, preferred_location, job_type, created_at, active) VALUES ('USER@EXAMPLE.COM','London','Any','2020',1)")
    cur.execute("INSERT INTO jobs (title, location, url) VALUES ('J','L','U')")
    job_id = cur.lastrowid
    cur.execute("INSERT INTO alert_deliveries (user_id, subscription_id, job_id, status, created_at) VALUES (?,?,?,'queued','2020')", (user_id, 1, job_id))
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM subscriptions")
    assert cur.fetchone()[0] == 1
    cur.execute("SELECT COUNT(*) FROM alert_deliveries")
    assert cur.fetchone()[0] == 1
    conn.close()

    user_store.delete_user_data(user_id)

    conn = sqlite3.connect(temp_db)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM subscriptions")
    assert cur.fetchone()[0] == 0
    cur.execute("SELECT COUNT(*) FROM alert_deliveries")
    assert cur.fetchone()[0] == 0
    cur.execute("SELECT COUNT(*) FROM users")
    assert cur.fetchone()[0] == 0
    conn.close()
