import sqlite3

from core.database import database_path


print("DB path:", database_path.resolve())

conn = sqlite3.connect(database_path)
cur = conn.cursor()
cur.execute("DELETE FROM jobs")
conn.commit()
conn.close()

print("[reset] jobs table cleared.")

