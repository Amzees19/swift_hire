import os

import pytest


if not os.getenv("DATABASE_URL"):
    pytest.skip("DATABASE_URL must be set for Postgres-only tests.", allow_module_level=True)

from core.db.base import get_conn
from core.db.schema import init_db, seed_default_locations


_TABLES = [
    "alert_deliveries",
    "activation_events",
    "email_verification_tokens",
    "password_reset_tokens",
    "sessions",
    "subscriptions",
    "deleted_subscriptions",
    "deleted_users",
    "jobs",
    "locations",
    "users",
]


def _truncate_all():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "TRUNCATE " + ", ".join(_TABLES) + " RESTART IDENTITY CASCADE"
    )
    conn.commit()
    conn.close()


@pytest.fixture(autouse=True)
def _clean_db():
    init_db()
    _truncate_all()
    seed_default_locations()
    yield
    _truncate_all()
