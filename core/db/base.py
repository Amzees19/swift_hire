"""
Low-level database helpers (Postgres-only).
"""
from __future__ import annotations

import os
from typing import Iterable

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception as exc:  # pragma: no cover - required dependency
    raise RuntimeError("psycopg is required for Postgres") from exc


def _resolve_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL must be set for Postgres usage")
    if url.startswith("postgres://") or url.startswith("postgresql://"):
        return url
    raise RuntimeError("DATABASE_URL must start with postgres:// or postgresql://")


database_url = _resolve_database_url()


def _convert_qmarks(sql: str) -> str:
    if "?" not in sql:
        return sql
    return sql.replace("?", "%s")


class _CursorWrapper:
    def __init__(self, cursor, dialect: str):
        self._cursor = cursor
        self._dialect = dialect

    def execute(self, sql: str, params: Iterable | None = None):
        if self._dialect == "postgres":
            sql = _convert_qmarks(sql)
        if params is None:
            return self._cursor.execute(sql)
        return self._cursor.execute(sql, params)

    def executemany(self, sql: str, seq_of_params: Iterable):
        if self._dialect == "postgres":
            sql = _convert_qmarks(sql)
        return self._cursor.executemany(sql, seq_of_params)

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def __iter__(self):
        return iter(self._cursor)

    @property
    def rowcount(self):
        return getattr(self._cursor, "rowcount", 0)

    @property
    def lastrowid(self):
        return getattr(self._cursor, "lastrowid", None)


class _ConnWrapper:
    def __init__(self, conn, dialect: str):
        self._conn = conn
        self.dialect = dialect

    def cursor(self):
        return _CursorWrapper(self._conn.cursor(), self.dialect)

    def commit(self):
        return self._conn.commit()

    def close(self):
        return self._conn.close()


def get_conn():
    """
    Return a Postgres DB connection (DATABASE_URL required).
    """
    conn = psycopg.connect(database_url, row_factory=dict_row)
    return _ConnWrapper(conn, "postgres")
