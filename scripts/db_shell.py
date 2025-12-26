"""
Quick helper to run a query against Postgres (DATABASE_URL required).

Usage:
  DATABASE_URL=... python scripts/db_shell.py                          # list tables
  DATABASE_URL=... python scripts/db_shell.py "SELECT * FROM users"    # run a custom query
"""
from __future__ import annotations

import os
import sys

import psycopg
from psycopg.rows import dict_row

def resolve_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL must be set for Postgres usage")
    if url.startswith("postgres://") or url.startswith("postgresql://"):
        return url
    raise SystemExit("DATABASE_URL must start with postgres:// or postgresql://")


DATABASE_URL = resolve_database_url()


def main() -> None:
    query = " ".join(sys.argv[1:]).strip()
    if not query:
        query = (
            "SELECT tablename AS name "
            "FROM pg_tables WHERE schemaname='public' "
            "ORDER BY tablename"
        )

    print("Using DB: postgres (DATABASE_URL)", file=sys.stderr)

    try:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            cur = conn.cursor()
            cur.execute(query)
            if cur.description is not None:
                rows = cur.fetchall()
                for row in rows:
                    print(dict(row))
            else:
                conn.commit()
                print(f"OK ({cur.rowcount} row(s) affected)")
    except Exception as exc:
        raise SystemExit(f"Error running query: {exc}") from exc


if __name__ == "__main__":
    main()
