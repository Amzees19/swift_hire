"""
One-off migration script to add activation_code to activation_events if missing.
Usage:
  python scripts/migrate_activation_code.py
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "jobs.db"


def ensure_activation_code_column() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(activation_events)")
    cols = [row[1] for row in cur.fetchall()]
    if "activation_code" in cols:
        print("activation_code already exists; no migration needed.")
        conn.close()
        return

    print("Migrating activation_events to add activation_code...")
    cur.execute("PRAGMA foreign_keys=off")
    cur.execute("BEGIN TRANSACTION")
    cur.execute(
        """
        CREATE TABLE activation_events_new(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activation_code TEXT UNIQUE,
            user_id INTEGER NOT NULL,
            subscription_id INTEGER NOT NULL,
            activated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(subscription_id) REFERENCES subscriptions(id)
        )
        """
    )
    cur.execute(
        "INSERT INTO activation_events_new (id, user_id, subscription_id, activated_at) "
        "SELECT id, user_id, subscription_id, activated_at FROM activation_events"
    )
    cur.execute("DROP TABLE activation_events")
    cur.execute("ALTER TABLE activation_events_new RENAME TO activation_events")
    cur.execute("COMMIT")
    cur.execute("PRAGMA foreign_keys=on")
    conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    ensure_activation_code_column()
