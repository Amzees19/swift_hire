---
title: Copilot instructions for amazon_alerts
---

This file gives immediate, actionable context for AI coding agents working in this repository.

1) Big picture
- Purpose: a small scraper + alert system that finds Amazon UK jobs and emails subscribers matching locations/types.
- Major components:
  - `api.py` – FastAPI web UI + subscription/login pages; seeds DB on startup via `init_db()`.
  - `amazon_engine.py` – Playwright-based scraper that loads Amazon jobs page and extracts jobs via text heuristics.
  - `main.py` – worker/worker-like runner that calls the engine, filters new jobs (`get_new_jobs`), matches against subscriptions and sends email alerts.
  - `database.py` – single SQLite DB (`jobs.db`) with tables: `jobs`, `locations`, `subscriptions`, `users`, `sessions`. All DB access uses `sqlite3` and simple helper functions.

2) Key workflows & dev commands (explicit)
- Start the web UI (development):
  - `uvicorn api:app --reload --port 8000`
  - Note: `api.py` calls `init_db()` on FastAPI startup so DB + seed locations are created automatically.
- Run the worker (scraper + mailer):
  - `python main.py`
  - `main.py` has `TEST_MODE = True` by default (uses fake jobs). Set `TEST_MODE = False` to enable real scraping.
- Quick checks / smoke tests (project uses simple test scripts, not pytest):
  - `python test_insert_jobs.py` — ensures DB exists and tests insertion dedup logic.
  - `python test_sessions.py` — smoke-checks user/session functions.

3) Project-specific patterns & conventions
- DB: `database_path` is `jobs.db` next to `database.py`. Many functions use `sqlite3` directly (no ORM). Expect `row_factory = sqlite3.Row` in read helpers and `INSERT OR IGNORE` for idempotent seeds.
- Locations/subscriptions: `preferred_location` stores a semicolon-separated string (`loc1; loc2; loc3`). `main.expand_preferred_locations` and `main.job_matches_subscription` implement matching logic and must be updated when changing area semantics.
- Unique job identity: `jobs` table uses `UNIQUE(title, location, url)` — dedup behavior is handled in `database.get_new_jobs` (it inserts and returns only newly-inserted rows).
- Sessions: cookie name `session_id` (see `api.SESSION_COOKIE_NAME`). Sessions are stored in DB (`sessions` table) and refreshed via `touch_session`.
- Passwords: bcrypt is used in `database.py` (`hash_password`, `verify_password`). Tests rely on these helpers.

4) Integration & dependencies (discoverable from imports)
- FastAPI: `api.py` (server + templates via string HTML). Use `uvicorn` to run.
- Playwright: `amazon_engine.py` imports `playwright.async_api` — to run real scraping ensure Playwright is installed and browsers installed (`pip install playwright` + `playwright install`).
- bcrypt: required for password hashing (`pip install bcrypt`).
- Email sending uses `smtplib` and credentials inside `main.py` (cleartext). Treat as test/dev only.

5) Files to edit for common tasks (examples)
- Add a new subscription/email behavior: change `api.py`'s `/subscribe` handler and `database.add_subscription`.
- Extend area groups or add canonical locations: edit `api.py` `AREA_GROUPS` and `database.DEFAULT_LOCATIONS`.
- Tweak scraping heuristics: edit `_parse_jobs_from_text` and `_find_job_url` in `amazon_engine.py`.

6) What to watch for / gotchas (useful for automated agents)
- There is no `requirements.txt` or lockfile. Before code that uses external packages, confirm availability or update repository to include `requirements.txt`.
- `main.py` defaults to `TEST_MODE = True`. Running the worker with `TEST_MODE=False` requires Playwright and a configured SMTP account.
- Database is local: `jobs.db` in the repo directory — tests and the running app will create and mutate that file. Be careful when making changes that rely on a clean DB state.
- UI templates are inline HTML strings in `api.py`. Small UI tweaks can be done directly in those functions.

7) Short examples for common commands
```powershell
# Run API server
uvicorn api:app --reload --port 8000

# Run worker (test mode)
python main.py

# Run quick scripts
python test_insert_jobs.py
python test_sessions.py
```

8) If you edit or add new modules
- Follow the local style: small, single-purpose modules; prefer explicit helper functions in `database.py` and `amazon_engine.py` for testability.
- Add or update quick test scripts similar to `test_insert_jobs.py` for any DB-changing logic.

If anything here is unclear or you want additional examples (e.g., a `requirements.txt` suggestion, a CI test script, or a short CONTRIBUTING note), tell me which area to expand.
