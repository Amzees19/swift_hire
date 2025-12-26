# #!/bin/sh
# set -e

# # Ensure the app and worker use the mounted Fly volume DB.
# export DATABASE_PATH="${DATABASE_PATH:-/data/jobs.db}"

# # Start the US worker in the background, then run the web app in the foreground.
# /app/.venv/bin/python -m worker.main_us &
# exec /app/.venv/bin/uvicorn app.api:app --host 0.0.0.0 --port 8000

#!/bin/sh
set -e

# Run only the web app
exec /app/.venv/bin/uvicorn app.api:app --host 0.0.0.0 --port 8000

