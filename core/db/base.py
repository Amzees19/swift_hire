"""
Low-level database helpers.
"""
from __future__ import annotations

import sqlite3
import os
from pathlib import Path

# Keep jobs.db at the project root even though this module is in core/db
# __file__ is .../core/db/base.py -> parents[0]=db, [1]=core, [2]=repo root
_default_path = Path(__file__).resolve().parents[2] / "jobs.db"

def _resolve_db_path() -> Path:
    """
    Resolve the database path from env var DATABASE_PATH if provided,
    otherwise default to the repo-root jobs.db. Allows mounting a
    persistent volume (e.g., /data/jobs.db) in hosted environments.
    """
    env_path = os.getenv("DATABASE_PATH")
    if env_path:
        try:
            return Path(env_path).expanduser().resolve(strict=False)
        except Exception:
            # Fall back to default if resolution fails
            return _default_path
    return _default_path


database_path = _resolve_db_path()


def get_conn() -> sqlite3.Connection:
    """Return a new sqlite3 connection with row_factory=sqlite3.Row."""
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    return conn
