import sqlite3
import tempfile

import pytest

from core.db.users import email_verification as ev


def setup_temp_db():
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
        CREATE TABLE email_verification_tokens(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used_at TEXT
        )
        """
    )
    conn.execute("INSERT INTO users (email, password_hash, role, active, created_at, email_verified_at) VALUES ('u@example.com','x','user',1,'2020',NULL)")
    conn.commit()
    conn.close()
    return tmp.name


@pytest.fixture()
def temp_db(monkeypatch):
    path = setup_temp_db()
    monkeypatch.setattr(ev, "database_path", path)
    return path


def test_create_and_fetch_verification_token(temp_db):
    token = ev.create_email_verification_token(user_id=1)
    row = ev.get_email_verification_token(token)
    assert row is not None
    assert row["user_id"] == 1


def test_token_single_use(temp_db):
    token = ev.create_email_verification_token(user_id=1)
    ev.mark_email_verification_token_used(token)
    assert ev.get_email_verification_token(token) is None


def test_mark_user_verified(temp_db):
    ev.mark_user_email_verified(1)
    conn = sqlite3.connect(ev.database_path)
    cur = conn.cursor()
    cur.execute("SELECT email_verified_at FROM users WHERE id=1")
    verified_at = cur.fetchone()[0]
    conn.close()
    assert verified_at is not None and verified_at != ""

