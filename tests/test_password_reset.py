import sqlite3
import tempfile
import time

import pytest

from core.db.users import password_reset as pr


def setup_temp_db():
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    conn = sqlite3.connect(tmp.name)
    conn.execute(
        """
        CREATE TABLE password_reset_tokens(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()
    return tmp.name


@pytest.fixture
def temp_db(monkeypatch):
    path = setup_temp_db()
    monkeypatch.setattr(pr, "database_path", path)
    return path


def test_create_and_fetch_token(temp_db):
    token = pr.create_password_reset_token(user_id=1)
    data = pr.get_password_reset_token(token)
    assert data is not None
    assert data["user_id"] == 1
    assert data["token"] == token


def test_token_single_use_and_expiry_cleanup(temp_db):
    token = pr.create_password_reset_token(user_id=2)
    # Mark used
    pr.mark_reset_token_used(token)
    assert pr.get_password_reset_token(token) is None

    # Expire a token manually and ensure cleanup
    conn = sqlite3.connect(pr.database_path)
    cur = conn.cursor()
    cur.execute("INSERT INTO password_reset_tokens (user_id, token, created_at, expires_at, used_at) VALUES (3, 'old', '2020', '2020', NULL)")
    conn.commit()
    conn.close()
    assert pr.get_password_reset_token("old") is None


def test_unknown_token_returns_none(temp_db):
    assert pr.get_password_reset_token("does-not-exist") is None
