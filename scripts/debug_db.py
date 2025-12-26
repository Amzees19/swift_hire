from core.db import get_conn, init_db

# Make sure schema exists
init_db()

conn = get_conn()
cur = conn.cursor()

# List tables
print("\nTables:")
cur.execute("SELECT tablename AS name FROM pg_tables WHERE schemaname='public'")
for row in cur.fetchall():
    print(" -", row["name"])

# ---- Users ----
print("\nUsers:")
cur.execute("SELECT id, email, password_hash, created_at FROM users")
users = cur.fetchall()
print(f"Total users: {len(users)}")
for u in users:
    print(dict(u))

# ---- Subscriptions ----
print("\nSubscriptions:")
cur.execute(
    "SELECT id, email, preferred_location, job_type, created_at FROM subscriptions"
)
subs = cur.fetchall()
print(f"Total subscriptions: {len(subs)}")
for s in subs:
    print(dict(s))

# ---- Jobs ----
print("\nJobs:")
cur.execute(
    "SELECT id, title, location, type, duration, pay, first_seen_at FROM jobs"
)
jobs = cur.fetchall()
print(f"Total jobs: {len(jobs)}")
for j in jobs:
    print(dict(j))

conn.close()
