import sqlite3
from core.database import database_path, init_db

# Ensure tables exist (does NOT wipe data)
init_db()

print("DB path used by core.database:", database_path.resolve())

conn = sqlite3.connect(database_path)
cur = conn.cursor()

print("\nTables:")
for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'"):
    print(" -", row[0])

print("\nJobs:")
try:
    rows = list(cur.execute("SELECT id, title, location, first_seen_at FROM jobs"))
    print(f"Total jobs: {len(rows)}")
    for r in rows:
        print(r)
except Exception as e:
    print("Error querying jobs table:", e)

conn.close()


