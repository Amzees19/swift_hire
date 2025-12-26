from core.db import get_conn, init_db

# Ensure tables exist (no data loss if file already exists)
init_db()

conn = get_conn()
cur = conn.cursor()

print("\nTables:")
cur.execute("SELECT tablename AS name FROM pg_tables WHERE schemaname='public'")
for row in cur.fetchall():
    print(" -", row["name"])

print("\nJobs:")
cur.execute("SELECT id, title, location, first_seen_at FROM jobs")
rows = cur.fetchall()
print(f"Total jobs: {len(rows)}")
for r in rows:
    print(dict(r))

conn.close()
