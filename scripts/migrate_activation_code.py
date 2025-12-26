"""
One-off Postgres migration to add activation_code to activation_events if missing.
Usage:
  DATABASE_URL=... python scripts/migrate_activation_code.py
"""
from __future__ import annotations

import os

import psycopg
from psycopg.rows import dict_row


def ensure_activation_code_column() -> None:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL must be set for Postgres usage")

    with psycopg.connect(url, row_factory=dict_row) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'activation_events'
            """
        )
        cols = {row["column_name"] for row in cur.fetchall()}
        if "activation_code" in cols:
            print("activation_code already exists; no migration needed.")
            return

        print("Adding activation_code column to activation_events...")
        cur.execute("ALTER TABLE activation_events ADD COLUMN activation_code TEXT UNIQUE")
        conn.commit()
        print("Migration complete.")


if __name__ == "__main__":
    ensure_activation_code_column()
