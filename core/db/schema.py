"""
Schema and migration helpers for SQLite.
"""
from __future__ import annotations

import os
import secrets
import sqlite3
from datetime import datetime
from typing import List

from core.db.base import database_path
from core.db.users import create_user, get_user_by_email, hash_password

# --- Canonical Amazon UK locations (real sites from public lists) ---
# You can add/remove rows here later if you want.
DEFAULT_LOCATIONS = [
    # Major cities / areas
    {"code": None, "name": "Birmingham", "region": "West Midlands"},
    {"code": None, "name": "Manchester", "region": "Greater Manchester"},
    {"code": None, "name": "Leeds", "region": "West Yorkshire"},
    {"code": None, "name": "London", "region": "Greater London"},
    {"code": None, "name": "Cardiff", "region": "Wales"},
    {"code": None, "name": "Swansea", "region": "Wales"},
    {"code": None, "name": "Bristol", "region": "South West"},
    {"code": None, "name": "Newport", "region": "Wales"},
    {"code": None, "name": "Glasgow", "region": "Scotland"},
    {"code": None, "name": "Edinburgh", "region": "Scotland"},
    {"code": None, "name": "Belfast", "region": "Northern Ireland"},
    # England – Midlands & North (actual FC / DS towns)
    {"code": "BHX1", "name": "Rugeley", "region": "Staffordshire"},
    {"code": "BHX2", "name": "Coalville", "region": "Leicestershire"},
    {"code": "BHX3", "name": "Daventry", "region": "Northamptonshire"},
    {"code": "BHX4", "name": "Coventry", "region": "West Midlands"},
    {"code": "BHX5", "name": "Rugby", "region": "Warwickshire"},
    {"code": "BHX8", "name": "Redditch", "region": "Worcestershire"},
    {"code": "MAN2", "name": "Warrington", "region": "Cheshire"},
    {"code": "MAN3", "name": "Bolton", "region": "Greater Manchester"},
    {"code": "MAN4", "name": "Chesterfield", "region": "Derbyshire"},
    {"code": "LBA1", "name": "Doncaster", "region": "South Yorkshire"},
    {"code": "LBA2", "name": "Doncaster (LBA2)", "region": "South Yorkshire"},
    {"code": "LBA3", "name": "Doncaster (LBA3)", "region": "South Yorkshire"},
    {"code": "LBA4", "name": "Doncaster (LBA4)", "region": "South Yorkshire"},
    {"code": "DXS1", "name": "Sheffield", "region": "South Yorkshire"},
    {"code": "NCL2", "name": "Billingham", "region": "County Durham"},
    {"code": "MME1", "name": "Darlington", "region": "County Durham"},
    {"code": "DPN1", "name": "Carlisle", "region": "Cumbria"},
    # England – South & East
    {"code": "LCY2", "name": "Tilbury", "region": "Essex"},
    {"code": "LCY3", "name": "Dartford", "region": "Kent"},
    {"code": "LCY8", "name": "Rochester", "region": "Kent"},
    {"code": "DME4", "name": "Aylesford", "region": "Kent"},
    {"code": "LTN1", "name": "Milton Keynes (Ridgmont)", "region": "Buckinghamshire"},
    {"code": "ALT1", "name": "Milton Keynes (Northfield)", "region": "Buckinghamshire"},
    {"code": "LTN7", "name": "Bedford", "region": "Bedfordshire"},
    # England – South West
    {"code": "BRS1", "name": "Bristol (BRS1)", "region": "South West"},
    {"code": "BRS2", "name": "Swindon", "region": "South West"},
    # Wales (FC / DS towns)
    {"code": "DCF1", "name": "Newport (DCF1)", "region": "Wales"},
    {"code": "CWL1", "name": "Port Talbot", "region": "Wales"},
    # Scotland
    {"code": "EDI4", "name": "Dunfermline", "region": "Scotland"},
    {"code": "DEH1", "name": "Edinburgh (DEH1)", "region": "Scotland"},
    {"code": "HEH1", "name": "Edinburgh (HEH1)", "region": "Scotland"},
    {"code": "DXG1", "name": "Glasgow (DXG1)", "region": "Scotland"},
    {"code": "DXG2", "name": "Glasgow (DXG2)", "region": "Scotland"},
    {"code": "DDD1", "name": "Dundee", "region": "Scotland"},
    {"code": "SEH1", "name": "Bathgate", "region": "Scotland"},
    # Northern Ireland – delivery stations
    {"code": None, "name": "Portadown", "region": "Northern Ireland"},

    # --- US test locations (added for cross-region testing) ---
    {"code": None, "name": "Weston", "region": "WI"},
    {"code": None, "name": "Charlton", "region": "MA"},
    {"code": None, "name": "Portland", "region": "OR"},
]


def init_db() -> None:
    """Create the jobs, locations, subscriptions, users, and sessions tables if they don't exist."""
    conn = sqlite3.connect(database_path)
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            type TEXT,
            duration TEXT,
            pay TEXT,
            location TEXT,
            url TEXT,
            first_seen_at TEXT,
            UNIQUE(title, location, url)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS locations(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            name TEXT NOT NULL,
            region TEXT,
            country TEXT DEFAULT 'United Kingdom',
            active INTEGER DEFAULT 1,
            UNIQUE(name, region, code)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS subscriptions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            email TEXT NOT NULL,
            preferred_location TEXT,
            job_type TEXT,
            created_at TEXT,
            active INTEGER DEFAULT 1,
            updated_once INTEGER DEFAULT 0,
            last_deactivated_at TEXT,
            needs_pref_update INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT
        )
        """
    )

    # Backfill role column for existing installs
    _ensure_role_column(cur)
    _ensure_active_column(cur)
    _ensure_email_verified_at_column(cur)
    _ensure_updated_once_column(cur)
    _ensure_subscriptions_new_columns(cur)
    _ensure_subscription_user_id_column(cur)
    _ensure_activation_code_column(cur)

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions(
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS activation_events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activation_code TEXT NOT NULL UNIQUE,
            user_id INTEGER NOT NULL,
            subscription_id INTEGER NOT NULL,
            activated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(subscription_id) REFERENCES subscriptions(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS password_reset_tokens(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS email_verification_tokens(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS alert_deliveries(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subscription_id INTEGER NOT NULL,
            job_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            created_at TEXT NOT NULL,
            sent_at TEXT,
            error TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(subscription_id) REFERENCES subscriptions(id),
            FOREIGN KEY(job_id) REFERENCES jobs(id),
            UNIQUE(subscription_id, job_id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS deleted_users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            email TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TEXT,
            deleted_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS deleted_subscriptions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subscription_id INTEGER NOT NULL,
            user_id INTEGER,
            email TEXT NOT NULL,
            preferred_location TEXT,
            job_type TEXT,
            created_at TEXT,
            active INTEGER,
            deleted_at TEXT NOT NULL
        )
        """
    )

    _ensure_subscription_user_id_backfill(cur)
    _ensure_user_delete_triggers(cur)

    conn.commit()
    conn.close()

    seed_default_locations()
    ensure_admin_from_env()
    backfill_users_from_subscriptions()


def _ensure_role_column(cur: sqlite3.Cursor) -> None:
    """Add a role column to users if missing, and backfill defaults."""
    cur.execute("PRAGMA table_info(users)")
    cols = [row[1] for row in cur.fetchall()]
    if "role" not in cols:
        try:
            cur.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
        except Exception:
            pass  # if migration fails, continue to avoid breaking startup
    cur.execute("UPDATE users SET role='user' WHERE role IS NULL OR role=''")


def _ensure_active_column(cur: sqlite3.Cursor) -> None:
    """Add an active column to users if missing, default to 1."""
    cur.execute("PRAGMA table_info(users)")
    cols = [row[1] for row in cur.fetchall()]
    if "active" not in cols:
        try:
            cur.execute("ALTER TABLE users ADD COLUMN active INTEGER NOT NULL DEFAULT 1")
        except Exception:
            pass
    cur.execute("UPDATE users SET active=1 WHERE active IS NULL")


def _ensure_email_verified_at_column(cur: sqlite3.Cursor) -> None:
    """
    Add an email_verified_at column to users if missing.
    When first added, backfill existing users as verified to avoid breaking existing installs.
    New users created after this migration will default to NULL (unverified).
    """
    cur.execute("PRAGMA table_info(users)")
    cols = [row[1] for row in cur.fetchall()]
    if "email_verified_at" not in cols:
        try:
            cur.execute("ALTER TABLE users ADD COLUMN email_verified_at TEXT")
            # Backfill all existing rows immediately (only runs on first migration)
            cur.execute("UPDATE users SET email_verified_at = datetime('now') WHERE email_verified_at IS NULL")
        except Exception:
            pass


def _ensure_updated_once_column(cur: sqlite3.Cursor) -> None:
    """Add an updated_once column to subscriptions if missing."""
    cur.execute("PRAGMA table_info(subscriptions)")
    cols = [row[1] for row in cur.fetchall()]
    if "updated_once" not in cols:
        try:
            cur.execute("ALTER TABLE subscriptions ADD COLUMN updated_once INTEGER DEFAULT 0")
        except Exception:
            pass
    cur.execute("UPDATE subscriptions SET updated_once=0 WHERE updated_once IS NULL")


def _ensure_subscriptions_new_columns(cur: sqlite3.Cursor) -> None:
    """Add last_deactivated_at and needs_pref_update to subscriptions if missing."""
    cur.execute("PRAGMA table_info(subscriptions)")
    cols = [row[1] for row in cur.fetchall()]
    if "last_deactivated_at" not in cols:
        try:
            cur.execute("ALTER TABLE subscriptions ADD COLUMN last_deactivated_at TEXT")
        except Exception:
            pass
    if "needs_pref_update" not in cols:
        try:
            cur.execute("ALTER TABLE subscriptions ADD COLUMN needs_pref_update INTEGER DEFAULT 0")
        except Exception:
            pass
    cur.execute("UPDATE subscriptions SET needs_pref_update=0 WHERE needs_pref_update IS NULL")


def _ensure_subscription_user_id_column(cur: sqlite3.Cursor) -> None:
    """Add user_id to subscriptions if missing."""
    cur.execute("PRAGMA table_info(subscriptions)")
    cols = [row[1] for row in cur.fetchall()]
    if "user_id" not in cols:
        try:
            cur.execute("ALTER TABLE subscriptions ADD COLUMN user_id INTEGER")
        except Exception:
            pass


def _ensure_subscription_user_id_backfill(cur: sqlite3.Cursor) -> None:
    """Backfill subscriptions.user_id based on email match."""
    try:
        cur.execute(
            """
            UPDATE subscriptions
            SET user_id = (
                SELECT id FROM users
                WHERE lower(users.email) = lower(subscriptions.email)
                LIMIT 1
            )
            WHERE user_id IS NULL
            """
        )
    except Exception:
        pass


def _ensure_user_delete_triggers(cur: sqlite3.Cursor) -> None:
    """
    Ensure user deletion cascades and archives rows.
    This protects manual/admin deletes outside of app logic.
    """
    try:
        cur.execute(
            """
            CREATE TRIGGER IF NOT EXISTS users_delete_archive
            BEFORE DELETE ON users
            FOR EACH ROW
            BEGIN
              INSERT INTO deleted_users(user_id, email, role, created_at, deleted_at)
              VALUES (OLD.id, OLD.email, OLD.role, OLD.created_at, datetime('now'));
            END;
            """
        )
        cur.execute(
            """
            CREATE TRIGGER IF NOT EXISTS subscriptions_delete_archive
            BEFORE DELETE ON subscriptions
            FOR EACH ROW
            BEGIN
              INSERT INTO deleted_subscriptions(
                subscription_id, user_id, email, preferred_location, job_type, created_at, active, deleted_at
              ) VALUES (
                OLD.id, OLD.user_id, OLD.email, OLD.preferred_location, OLD.job_type, OLD.created_at, OLD.active, datetime('now')
              );
            END;
            """
        )
        cur.execute(
            """
            CREATE TRIGGER IF NOT EXISTS users_delete_cascade
            AFTER DELETE ON users
            FOR EACH ROW
            BEGIN
              DELETE FROM subscriptions WHERE user_id = OLD.id OR lower(email) = lower(OLD.email);
              DELETE FROM alert_deliveries WHERE user_id = OLD.id;
              DELETE FROM sessions WHERE user_id = OLD.id;
              DELETE FROM password_reset_tokens WHERE user_id = OLD.id;
              DELETE FROM email_verification_tokens WHERE user_id = OLD.id;
            END;
            """
        )
    except Exception:
        pass


def _ensure_activation_code_column(cur: sqlite3.Cursor) -> None:
    """Add activation_code to activation_events if missing."""
    cur.execute("PRAGMA table_info(activation_events)")
    cols = [row[1] for row in cur.fetchall()]
    if "activation_code" not in cols:
        try:
            cur.execute("ALTER TABLE activation_events ADD COLUMN activation_code TEXT UNIQUE")
        except Exception:
            pass


def seed_default_locations() -> None:
    """Insert DEFAULT_LOCATIONS into the locations table (idempotent)."""
    conn = sqlite3.connect(database_path)
    cur = conn.cursor()

    for loc in DEFAULT_LOCATIONS:
        cur.execute(
            """
            INSERT OR IGNORE INTO locations (code, name, region, country, active)
            VALUES (?, ?, ?, ?, 1)
            """,
            (
                loc.get("code"),
                loc.get("name"),
                loc.get("region"),
                loc.get("country") or "United Kingdom",
            ),
        )

    conn.commit()
    conn.close()


def ensure_admin_from_env() -> None:
    """
    Optionally seed/update an admin account from environment variables.
    Set ADMIN_EMAIL and ADMIN_PASSWORD before startup to use.
    """
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")

    if not admin_email or not admin_password:
        return

    existing = get_user_by_email(admin_email)
    if existing:
        # If already admin, nothing to do; otherwise promote and reset password.
        if existing.get("role") != "admin":
            conn = sqlite3.connect(database_path)
            cur = conn.cursor()
            cur.execute(
                "UPDATE users SET role='admin' WHERE email = ?",
                (admin_email.strip().lower(),),
            )
            conn.commit()
            conn.close()
        # Refresh password hash to match env-provided password
        conn = sqlite3.connect(database_path)
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET password_hash=? WHERE email=?",
            (hash_password(admin_password), admin_email.strip().lower()),
        )
        conn.commit()
        conn.close()
        # Mark admin as verified (admins are managed out-of-band)
        conn = sqlite3.connect(database_path)
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET email_verified_at = datetime('now') WHERE email = ? AND (email_verified_at IS NULL OR email_verified_at = '')",
            (admin_email.strip().lower(),),
        )
        conn.commit()
        conn.close()
        return

    # Create a new admin user
    create_user(admin_email, admin_password, role="admin", verified=True)


def backfill_users_from_subscriptions() -> None:
    """
    For legacy data where subscriptions exist but users were never created,
    create user accounts (with random passwords) for those emails.
    """
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        """
        SELECT DISTINCT email FROM subscriptions
        WHERE email NOT IN (SELECT email FROM users)
        """
    )
    missing = [row["email"] for row in cur.fetchall()]

    conn.close()

    if not missing:
        return

    for email in missing:
        temp_pwd = secrets.token_urlsafe(12)
        try:
            create_user(email, temp_pwd, role="user", verified=True)
            print(f"[db] Backfilled user for subscription email={email}")
        except Exception as exc:
            print(f"[db] Failed to backfill user for {email}: {exc}")


__all__ = [
    "DEFAULT_LOCATIONS",
    "init_db",
    "seed_default_locations",
    "ensure_admin_from_env",
    "backfill_users_from_subscriptions",
]
