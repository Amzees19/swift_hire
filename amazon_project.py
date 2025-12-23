# Amazon Job Alert Web App – MVP Plan
# ===================================

# Goal
# ----

# Build a small, lightweight web-based tool that:

# - Scrapes Amazon warehouse-style jobs (like the current Python + Playwright script).
# - Lets users choose:
#   - Preferred location (e.g. "Wales", "Birmingham", "Swansea").
#   - Preferred job type (Full-time, Part-time, Fixed-term/Seasonal, Any).
# - Emails users when NEW matching jobs appear.

# Constraints / Principles
# ------------------------

# - Keep stack simple and cheap (single server / VM, Python-based).
# - No heavy authentication for v1 (email-only subscriptions).
# - Be respectful to Amazon (modest scraping frequency, no hammering).
# - Design so it can later:
#   - Add more filters (pay, shift keywords, etc.).
#   - Add more job sources (other sites, supermarkets, seasonal work).
#   - Plug in a nicer frontend (Next.js, etc.) without rewriting core logic.

# MVP Scope (What v1 MUST Do)
# ---------------------------

# 1. Scrape current Amazon jobs
#    - Use existing Playwright logic.
#    - Return a list of structured job objects.

# 2. Filter jobs by user preferences
#    - Location: substring match in the job location string.
#    - Job type: match against job type/duration (or "Any").

# 3. Store jobs
#    - Persist jobs in a small database (SQLite) to avoid re-alerting on the same job.

# 4. Handle subscriptions
#    - Store: email, preferred location, job type, active flag.

# 5. Alert mechanism
#    - For each new job:
#      - Match against subscriptions.
#      - Send email alerts to matched users.

# 6. Simple web form
#    - One basic page where users can:
#      - Enter email.
#      - Enter preferred location text.
#      - Choose job type from a dropdown.
#    - On submit: save subscription and show a basic “You’re subscribed” message.

# Tech Stack
# ----------

# - Language: Python 3
# - Scraping: Playwright (already working)
# - Web backend: FastAPI
# - Database: SQLite
# - Email: Python smtplib with Gmail app password (for v1)
# - Frontend (v1): Simple HTML templates via FastAPI + Jinja2
#   - Future: optional Next.js frontend consuming FastAPI as an API.

# High-Level Architecture
# -----------------------

# 1. Scraper Engine (amazon_engine.py)
#    - Responsibility:
#      - Interact with Amazon site via Playwright.
#      - Handle cookies, modals, and text extraction.
#      - Parse jobs into structured objects.
#    - Public interface:
#      - async def fetch_jobs() -> list[dict]

# 2. Storage Layer (db.py)
#    - Responsibility:
#      - Initialise and manage SQLite.
#      - Store and retrieve jobs and subscriptions.
#    - Functions:
#      - init_db()
#      - insert_job(job)
#      - job_exists(job)
#      - insert_subscription(...)
#      - get_active_subscriptions()

# 3. Matcher + Notifier (worker.py)
#    - Responsibility:
#      - Periodically call fetch_jobs().
#      - Compare with stored jobs to identify new ones.
#      - Match new jobs to subscriptions.
#      - Send email alerts.

# 4. Web API & UI (app/main.py)
#    - Responsibility:
#      - Provide a simple UI and HTTP endpoints.
#    - Endpoints:
#      - GET /         -> Landing page + subscription form.
#      - POST /subscribe -> Save subscription, return confirmation.
#      - GET /health   -> Basic health check.

# Data Model (v1)
# ---------------

# Table: Job
# - id            INTEGER PRIMARY KEY
# - title         TEXT
# - type          TEXT
# - duration      TEXT
# - pay           TEXT
# - location      TEXT
# - url           TEXT
# - first_seen_at DATETIME
# - last_seen_at  DATETIME

# Uniqueness heuristic:
# - (title, location, url) combined should identify a job.

# Table: Subscription
# - id                 INTEGER PRIMARY KEY
# - email              TEXT
# - preferred_location TEXT   (e.g. "wales", "birmingham")
# - job_type           TEXT   ("Any", "Full Time", "Part Time", "Fixed-term")
# - created_at         DATETIME
# - active             BOOLEAN

# Matching Rules (MVP)
# --------------------

# For each new job:

# - Normalise strings to lowercase when comparing.
# - A subscription matches a job if:

#   - job.location.lower() contains subscription.preferred_location.lower()
#     (if preferred_location is non-empty),

#   AND

#   - subscription.job_type == "Any"
#     OR subscription.job_type.lower() is contained within job.type.lower()
#     OR subscription.job_type.lower() is contained within job.duration.lower().

# Examples:
# - Preferred location = "wales" matches "Garden City, Wales".
# - job_type "Fixed-term" matches jobs where duration includes "Fixed-term".
# - job_type "Any" matches all jobs regardless of type/duration.

# Roadmap & Milestones
# --------------------

# Milestone 1 – Extract & Clean the Scraper Engine
# ------------------------------------------------

# Goal:
# - Turn current script into a reusable engine function.

# Tasks:
# - Create amazon_engine.py.
# - Move Playwright logic into:
#   - async def fetch_jobs() -> list[dict]:
#     - Returns: [{title, type, duration, pay, location, url}, ...]
# - Create test_engine.py:
#   - Calls fetch_jobs() and prints results.
# - Verify that current live job(s) (e.g. Warehouse Operative) appear correctly.

# Milestone 2 – Add Filtering (No DB Yet)
# ---------------------------------------

# Goal:
# - Support location + job type filters in pure Python.

# Tasks:
# - In amazon_engine.py add:

#   def filter_jobs(jobs, preferred_location: str | None, job_type: str | None) -> list[dict]:

# - Implement simple matching rules described above.
# - Test:
#   - jobs = await fetch_jobs()
#   - filtered = filter_jobs(jobs, "wales", "Fixed-term")

# Milestone 3 – Introduce Database & Basic Global Alerts
# ------------------------------------------------------

# Goal:
# - Persist jobs and avoid alerting on the same job multiple times globally.

# Tasks:
# - Create db.py:
#   - init_db() to create tables (Jobs, later Subscriptions).
#   - insert_job(job_dict)
#   - job_exists(job_dict) to check by (title, location, url).
# - Create alert_cli.py:
#   - Fetch jobs via fetch_jobs().
#   - For each job:
#     - If job does not exist in DB:
#       - Insert job.
#       - Add to new_jobs list.
#   - If new_jobs is not empty:
#     - Send one email to your own email with all new jobs.

# At this point:
# - You have a persistent record of jobs.
# - You have a one-user alert flow working off the DB.

# Milestone 4 – FastAPI Web App + Subscriptions
# ---------------------------------------------

# Goal:
# - Allow anyone to subscribe via a small web form.

# Tasks:
# - Create app/main.py with FastAPI app:
#   - GET /:
#     - Returns an HTML page with:
#       - Email field.
#       - Preferred location field.
#       - Job type dropdown ("Any", "Full Time", "Part Time", "Fixed-term").
#   - POST /subscribe:
#     - Accepts form data.
#     - Saves an active subscription in the DB.
#     - Returns a confirmation page.
#   - GET /health:
#     - Returns {"status": "ok"}.

# - Extend db.py with Subscription helpers:
#   - insert_subscription(email, preferred_location, job_type)
#   - get_active_subscriptions()

# Milestone 5 – Worker Matching Jobs to Subscriptions
# ---------------------------------------------------

# Goal:
# - Deliver personalised alerts to each subscriber.

# Tasks:
# - Create worker.py:
#   - Loop every X seconds (e.g. 600 seconds / 10 minutes):
#     - Call fetch_jobs().
#     - Identify new jobs vs DB (insert new ones).
#     - Load active subscriptions.
#     - For each new job:
#       - For each subscription:
#         - If job matches subscription filters:
#           - Queue/send an email to that subscriber.
#     - Sleep and repeat.

# - For v1:
#   - Only send a job once globally (first time it appears).
#   - Later: optionally add DeliveryLog table to ensure each user gets each job only once even if worker restarts.

# Immediate Next Step (When Starting)
# -----------------------------------

# 1. Extract the current working scraping logic into amazon_engine.py.
# 2. Implement async fetch_jobs() and test_engine.py.
# 3. Confirm fetch_jobs() returns a clean list of job dicts.

# Once that’s stable, move step by step into:
# - Filtering,
# - SQLite,
# - FastAPI UI,
# - Background worker.

# Start small and build up in layers.
