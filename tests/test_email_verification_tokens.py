from core.db.base import get_conn
from core.db.users import email_verification as ev


def _seed_user():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO users (email, password_hash, role, active, created_at, email_verified_at)
        VALUES (?, ?, ?, 1, ?, NULL)
        RETURNING id
        """,
        ("u@example.com", "x", "user", "2020-01-01T00:00:00"),
    )
    user_id = int(cur.fetchone()["id"])
    conn.commit()
    conn.close()
    return user_id


def test_create_and_fetch_verification_token():
    user_id = _seed_user()
    token = ev.create_email_verification_token(user_id=user_id)
    row = ev.get_email_verification_token(token)
    assert row is not None
    assert row["user_id"] == user_id


def test_token_single_use():
    user_id = _seed_user()
    token = ev.create_email_verification_token(user_id=user_id)
    ev.mark_email_verification_token_used(token)
    assert ev.get_email_verification_token(token) is None


def test_mark_user_verified():
    user_id = _seed_user()
    ev.mark_user_email_verified(user_id)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT email_verified_at FROM users WHERE id=?", (user_id,))
    verified_at = cur.fetchone()["email_verified_at"]
    conn.close()
    assert verified_at is not None and verified_at != ""
