import sqlite3
from core.database import database_path, init_db

# Ensure tables exist (no data loss if file already exists)
init_db()

print("DB path used by core.database:", database_path.resolve())

conn = sqlite3.connect(database_path)
cur = conn.cursor()

print("\nTables:")
for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'"):
    print(" -", row[0])

print("\nJobs:")
rows = list(cur.execute("SELECT id, title, location, first_seen_at FROM jobs"))
print(f"Total jobs: {len(rows)}")
for r in rows:
    print(r)

conn.close()
