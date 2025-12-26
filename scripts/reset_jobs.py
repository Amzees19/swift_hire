from core.db import get_conn

conn = get_conn()
cur = conn.cursor()
cur.execute("DELETE FROM jobs")
conn.commit()
conn.close()

print("[reset] jobs table cleared.")
