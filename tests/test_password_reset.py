from core.db.base import get_conn
from core.db.users import password_reset as pr


def test_create_and_fetch_token():
    token = pr.create_password_reset_token(user_id=1)
    data = pr.get_password_reset_token(token)
    assert data is not None
    assert data["user_id"] == 1
    assert data["token"] == token


def test_token_single_use_and_expiry_cleanup():
    token = pr.create_password_reset_token(user_id=2)
    pr.mark_reset_token_used(token)
    assert pr.get_password_reset_token(token) is None

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO password_reset_tokens (user_id, token, created_at, expires_at, used_at)
        VALUES (?, ?, ?, ?, NULL)
        """,
        (3, "old", "2020-01-01T00:00:00", "2020-01-01T00:00:00"),
    )
    conn.commit()
    conn.close()

    assert pr.get_password_reset_token("old") is None


def test_unknown_token_returns_none():
    assert pr.get_password_reset_token("does-not-exist") is None
