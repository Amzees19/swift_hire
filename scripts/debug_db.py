import sqlite3
from core.database import database_path, init_db

# Make sure schema exists
init_db()

print("DB path from core.database:", database_path.resolve())

conn = sqlite3.connect(database_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# List tables
print("\nTables:")
for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'"):
    print(" -", row["name"])

# ---- Users ----
print("\nUsers:")
users = list(cur.execute("SELECT id, email, password_hash, created_at FROM users"))
print(f"Total users: {len(users)}")
for u in users:
    print(dict(u))

# ---- Subscriptions ----
print("\nSubscriptions:")
subs = list(
    cur.execute(
        "SELECT id, email, preferred_location, job_type, created_at FROM subscriptions"
    )
)
print(f"Total subscriptions: {len(subs)}")
for s in subs:
    print(dict(s))

# ---- Jobs ----
print("\nJobs:")
jobs = list(
    cur.execute(
        "SELECT id, title, location, type, duration, pay, first_seen_at FROM jobs"
    )
)
print(f"Total jobs: {len(jobs)}")
for j in jobs:
    print(dict(j))

conn.close()
