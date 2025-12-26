from core.db.base import get_conn
from core.db.users import password_reset as pr


def _seed_user(email: str) -> int:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO users (email, password_hash, role, active, created_at)
            VALUES (%s, %s, 'user', 1, now())
            ON CONFLICT (email) DO NOTHING
            RETURNING id
            """,
            (email, "x"),
        )
        row = cur.fetchone()
        if not row:
            cur.execute("SELECT id FROM users WHERE email=%s", (email,))
            row = cur.fetchone()
        conn.commit()
        if isinstance(row, dict):
            return int(row["id"])
        return int(row[0])
    finally:
        conn.close()


def test_create_and_fetch_token():
    user_id = _seed_user("user1@example.com")
    token = pr.create_password_reset_token(user_id=user_id)
    data = pr.get_password_reset_token(token)
    assert data is not None
    assert data["user_id"] == user_id
    assert data["token"] == token


def test_token_single_use_and_expiry_cleanup():
    user_id = _seed_user("user2@example.com")
    old_user_id = _seed_user("user3@example.com")
    token = pr.create_password_reset_token(user_id=user_id)
    pr.mark_reset_token_used(token)
    assert pr.get_password_reset_token(token) is None

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO password_reset_tokens (user_id, token, created_at, expires_at, used_at)
            VALUES (%s, %s, %s, %s, NULL)
            """,
            (old_user_id, "old", "2020-01-01T00:00:00", "2020-01-01T00:00:00"),
        )
        conn.commit()
    finally:
        conn.close()

    assert pr.get_password_reset_token("old") is None


def test_unknown_token_returns_none():
    assert pr.get_password_reset_token("does-not-exist") is None
