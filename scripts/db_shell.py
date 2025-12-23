"""
Quick helper to run a SQLite query against jobs.db.

Usage:
  python scripts/db_shell.py                          # list tables
  python scripts/db_shell.py "SELECT * FROM users"    # run a custom query
  DATABASE_PATH=/data/jobs.db python scripts/db_shell.py "SELECT COUNT(*) FROM users"
"""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path


def resolve_db_path() -> Path:
    # Explicit override always wins
    env_path = os.getenv("DATABASE_PATH")
    if env_path:
        return Path(env_path).expanduser()

    # On Fly, default to the mounted volume
    if os.getenv("FLY_APP_NAME"):
        return Path("/data/jobs.db")

    # Local dev default: repo root jobs.db (../jobs.db from scripts/)
    return Path(__file__).resolve().parent.parent / "jobs.db"


DB_PATH = resolve_db_path()


def main() -> None:
    query = " ".join(sys.argv[1:]).strip()
    if not query:
        query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"

    if not DB_PATH.exists():
        raise SystemExit(f"DB file not found: {DB_PATH}")

    # Show DB path so there's never any ambiguity
    print(f"Using DB: {DB_PATH}", file=sys.stderr)

    try:
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(query)

            # If the statement returns columns, it's a result set
            if cur.description is not None:
                rows = cur.fetchall()
                for row in rows:
                    print(dict(row))
            else:
                conn.commit()
                print(f"OK ({cur.rowcount} row(s) affected)")
    except sqlite3.Error as exc:
        raise SystemExit(f"SQLite error: {exc}") from exc
    except Exception as exc:
        raise SystemExit(f"Error running query: {exc}") from exc


if __name__ == "__main__":
    main()
