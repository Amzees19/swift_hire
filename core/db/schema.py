"""
Schema and migration helpers for Postgres.
"""
from __future__ import annotations

import os
import secrets
from datetime import datetime

from core.db.base import get_conn
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
    # England - Midlands & North (actual FC / DS towns)
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
    # England - South & East
    {"code": "LCY2", "name": "Tilbury", "region": "Essex"},
    {"code": "LCY3", "name": "Dartford", "region": "Kent"},
    {"code": "LCY8", "name": "Rochester", "region": "Kent"},
    {"code": "DME4", "name": "Aylesford", "region": "Kent"},
    {"code": "LTN1", "name": "Milton Keynes (Ridgmont)", "region": "Buckinghamshire"},
    {"code": "ALT1", "name": "Milton Keynes (Northfield)", "region": "Buckinghamshire"},
    {"code": "LTN7", "name": "Bedford", "region": "Bedfordshire"},
    # England - South West
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
    # Northern Ireland - delivery stations
    {"code": None, "name": "Portadown", "region": "Northern Ireland"},

    # --- US test locations (added for cross-region testing) ---
    {"code": None, "name": "Weston", "region": "WI"},
    {"code": None, "name": "Charlton", "region": "MA"},
    {"code": None, "name": "Portland", "region": "OR"},
]


def init_db() -> None:
    """Create the jobs, locations, subscriptions, users, and sessions tables if they don't exist."""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users(
            id SERIAL PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT,
            email_verified_at TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs(
            id SERIAL PRIMARY KEY,
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
            id SERIAL PRIMARY KEY,
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
            id SERIAL PRIMARY KEY,
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
            id SERIAL PRIMARY KEY,
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
            id SERIAL PRIMARY KEY,
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
            id SERIAL PRIMARY KEY,
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
            id SERIAL PRIMARY KEY,
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
            id SERIAL PRIMARY KEY,
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
            id SERIAL PRIMARY KEY,
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

    conn.commit()
    conn.close()

    seed_default_locations()
    ensure_admin_from_env()
    backfill_users_from_subscriptions()


def seed_default_locations() -> None:
    """Insert DEFAULT_LOCATIONS into the locations table (idempotent)."""
    conn = get_conn()
    cur = conn.cursor()

    for loc in DEFAULT_LOCATIONS:
        cur.execute(
            """
            INSERT INTO locations (code, name, region, country, active)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT (name, region, code) DO NOTHING
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
    now = datetime.utcnow().isoformat(timespec="seconds")

    if existing:
        conn = get_conn()
        cur = conn.cursor()
        if existing.get("role") != "admin":
            cur.execute(
                "UPDATE users SET role='admin' WHERE email = ?",
                (admin_email.strip().lower(),),
            )
        cur.execute(
            "UPDATE users SET password_hash=? WHERE email=?",
            (hash_password(admin_password), admin_email.strip().lower()),
        )
        cur.execute(
            "UPDATE users SET email_verified_at = ? WHERE email = ? AND (email_verified_at IS NULL OR email_verified_at = '')",
            (now, admin_email.strip().lower()),
        )
        conn.commit()
        conn.close()
        return

    create_user(admin_email, admin_password, role="admin", verified=True)


def backfill_users_from_subscriptions() -> None:
    """
    For legacy data where subscriptions exist but users were never created,
    create user accounts (with random passwords) for those emails.
    """
    conn = get_conn()
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
