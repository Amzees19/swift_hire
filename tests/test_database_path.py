from core.db import base


def test_database_url_is_postgres():
    assert base.database_url.startswith(("postgres://", "postgresql://"))
