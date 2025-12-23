# Quick reference commands (run from repo root). These are comments only; copy/paste as needed.

# Install dependencies (includes httpx for TestClient)
# python -m pip install -r requirements.txt
# python -m pip install httpx

# Run the full test suite
# python -m pytest

# Run focused test files
# python -m pytest tests/test_validation.py
# python -m pytest tests/test_security_headers.py
# python -m pytest tests/test_security_auth.py
# python -m pytest tests/test_session_and_rate_limits.py
# python -m pytest tests/test_password_reset.py tests/test_password_reset_flow.py
# python -m pytest tests/test_matching_us.py tests/test_matching_my_alerts.py
# python -m pytest tests/test_worker_email.py
# python -m pytest tests/test_jobs_dedup.py tests/test_database_path.py
# python -m pytest tests/test_auth_flow.py

# Start the API locally (with env vars loaded)
# python -m dotenv run -- python -m uvicorn app.api:app --reload

# Run the UK worker (live scraping)
# python -m dotenv run -- python -m worker.main

# Run the US worker
# python -m dotenv run -- python -m worker.main_us

# Inspect the database (example query)
# python scripts/db_shell.py "SELECT id,email,role,active,created_at FROM users"
# python scripts/db_shell.py "SELECT * FROM jobs ORDER BY datetime(first_seen_at) DESC LIMIT 5"

# Reset or debug jobs (examples)
# python scripts/debug_jobs.py
# python scripts/test_insert_jobs.py

# Migrate activation codes (idempotent)
# python scripts/migrate_activation_code.py
