"""
====================================================
Amazon Job Alert Web App – Progress Log
====================================================
Date: 2025-12-05
Project: amazon_alerts
Author: (me)

High-Level Summary
------------------
- Started from a single Playwright script that:
  - Opened jobsatamazon.co.uk
  - Removed geolocation/cookie pop-ups
  - Parsed page text
  - Emailed myself when a job existed.

- Gradually evolved into a small, structured system:
  - Scraper engine (amazon_engine.py)
  - Storage layer (database.py with SQLite)
  - Web API (api.py with FastAPI)
  - Worker / matcher (main.py) + test harnesses.

The system now:
- Can be driven in TEST_MODE with fake jobs.
- Stores jobs and subscriptions in a real DB.
- Matches jobs to user preferences.
- Sends real emails to subscribers.
- Is ready to switch to live scraping as soon as Amazon posts jobs again.


1) Scraper Engine – amazon_engine.py
------------------------------------
- Implemented async fetch_jobs() which:
  - Launches Playwright (Chromium).
  - Goes to Amazon jobs search page.
  - Handles:
    - Cookie banner (Accept all / Continue etc.).
    - Sticky alerts ("Close sticky alerts").
    - Geolocation / step modals (removed via JS).
  - Waits for React content to render, scrolls page once if needed.
  - Collects all visible text from all frames.
  - Parses page text into structured job dicts via parse_jobs_from_text():
    - Each job has:
      - title
      - type
      - duration
      - pay
      - location
      - url (best-effort; falls back to main search URL if not found).

- Confirmed behaviour:
  - When Amazon had a “Warehouse Operative – Garden City, Wales” job:
    - Script detected "1 job found" and parsed it correctly.
  - Currently (Dec 2025) Amazon often shows "0 jobs found":
    - fetch_jobs() correctly returns an empty list.
  - Geolocation warning ("We couldn’t get your location") does not stop parsing.


2) Storage Layer – database.py
------------------------------
- DB file: jobs.db (same folder as project scripts).
- Tables created by init_db():

  1) jobs
     - id INTEGER PRIMARY KEY AUTOINCREMENT
     - title TEXT NOT NULL
     - type TEXT
     - duration TEXT
     - pay TEXT
     - location TEXT
     - url TEXT
     - first_seen_at TEXT
     - UNIQUE(title, location, url)

  2) locations
     - Stores canonical Amazon UK locations + major cities:
       - Birmingham, Manchester, London, Leeds, Cardiff, Swansea, etc.
       - FC/DS towns like Rugeley (BHX1), Coventry (BHX4), Aylesford (DME4), etc.
     - Seeded once via seed_default_locations() using DEFAULT_LOCATIONS.

  3) subscriptions
     - id INTEGER PRIMARY KEY AUTOINCREMENT
     - email TEXT NOT NULL
     - preferred_location TEXT (free text; can hold multiple locations or area labels)
     - job_type TEXT
     - created_at TEXT
     - active INTEGER DEFAULT 1

- Functions:
  - init_db():
    - Creates tables if they don’t exist.
    - Seeds the locations table with DEFAULT_LOCATIONS.
  - get_locations():
    - Returns active locations (for potential UI use later).
  - get_new_jobs(jobs: list[dict]) -> list[dict]:
    - Inserts job rows into jobs table.
    - Uses UNIQUE(title, location, url) to avoid duplicates.
    - Returns only jobs that were newly inserted this run.
    - Debug print shows:
      - before count
      - after count
      - how many were inserted.
  - add_subscription(email, preferred_location, job_type):
    - Inserts an active subscription row.
  - get_active_subscriptions() -> list[dict]:
    - Returns all active subscriptions as list of dicts.

- Verified with:
  - test_insert_jobs.py:
    - First run: inserted 3 fake jobs into jobs.db.
    - Subsequent runs: 0 new inserted (UNIQUE constraint working).
  - debug_jobs.py:
    - Shows tables and confirms 3 rows in jobs table, e.g.:
      - (1, 'Warehouse Operative – Coventry', 'Coventry, United Kingdom', '2025-12-05T16:27:37')
      - (2, 'Warehouse Operative – Swansea', 'Swansea, Wales', '2025-12-05T16:27:37')
      - (3, 'Warehouse Operative – London', 'London, United Kingdom', '2025-12-05T16:27:37')


3) Web API & UI – api.py (FastAPI)
----------------------------------
- FastAPI app exposed via uvicorn:

  - GET "/" (Landing / Subscribe page)
    - Simple HTML form with:
      - Email address input.
      - Preferred location text area (user can type area labels or free locations).
      - Job type dropdown (e.g. Any / Full Time / Part Time / Fixed-term).
    - Submits to POST /subscribe.

  - POST "/subscribe"
    - Reads form data (email, preferred_location, job_type).
    - Calls add_subscription(email, preferred_location, job_type).
    - Returns a basic confirmation HTML page.

  - GET "/health"
    - Returns JSON: {"status": "ok"} used as a simple health check.

- Dependencies:
  - python-multipart installed to support form data.
  - Verified server start via:
    - python -m uvicorn api:app --reload
  - Form submissions confirmed:
    - debug.py shows multiple subscriptions stored, e.g.:
      - preferred_location examples:
        - "Birmingham / Midlands"
        - "Leeds / Yorkshire; East of England; Aylesford"
        - "Birmingham / Midlands; London commuter belt / South East; London (inner)"


4) Location Matching & Area Groups
----------------------------------
- Introduced AREA_GROUPS (in api.py/main.py) to map area labels to lists of towns:

  - Examples:
    - "Birmingham / Midlands" ->
      ["Birmingham", "Rugeley", "Coalville", "Daventry", "Coventry",
       "Rugby", "Hinckley", "Redditch", "Stoke-on-Trent", "Wednesbury",
       "Mansfield", "Eastwood", "Kegworth", "Northampton", "Banbury",
       "Burton-on-Trent"]

    - "London commuter belt / South East" ->
      ["Tilbury", "Dartford", "Rochester", "Aylesford", "Harlow", "Grays", "Weybridge"]

    - "London (inner)" ->
      ["London", "Barking", "Croydon", "Enfield", "Bexley", "Neasden", "Orpington"]

    - "Leeds / Yorkshire" ->
      ["Leeds", "Doncaster", "Wakefield", "Sheffield", "Hull", "North Ferriby"]

    - "East of England" ->
      ["Bedford", "Milton Keynes", "Ridgmont", "Dunstable", "Peterborough",
       "Norwich", "Ipswich", "Cambridge"]

- When a subscription has preferred_location like:
  - "Birmingham / Midlands; London commuter belt / South East; London (inner)"
- The worker expands that into a token list:
  - ["birmingham", "rugeley", "coalville", ..., "tilbury", "dartford", ... "london", "barking", ...]
- Matching rule:
  - job location is converted to lowercase.
  - If any token is a substring of the job location string, that job is considered a match for that subscription.
- This gives more flexible behaviour than a single substring:
  - Users can choose one or multiple large “areas” and we expand into all likely warehouse towns and surrounding locations.


5) Worker / Matcher – main.py
-----------------------------
- Acts as the background job processor (currently run manually):

  - init_db() at start:
    - Ensures schema exists and locations are seeded.
  
  - TEST_MODE flag:
    - When TEST_MODE = True:
      - Uses a fixed list of fake jobs, e.g.:
        - Warehouse Operative – Coventry
        - Warehouse Operative – Swansea
        - Warehouse Operative – London
      - Passes them to get_new_jobs() to simulate real scraping.
      - Confirms new jobs are inserted into jobs table.

    - When TEST_MODE = False:
      - Will call amazon_engine.fetch_jobs(headless=False or True) to scrape real jobs.

  - For each run:
    - Fetch jobs (real or fake).
    - Call get_new_jobs() -> new_jobs list.
    - Load active subscriptions from DB.
    - For each subscription:
      - Expand preferred_location via AREA_GROUPS into tokens.
      - Match each new job’s location against those tokens.
      - Check job_type:
        - If subscription.job_type == "Any" -> accept all.
        - Else require “Full Time”, “Part Time”, or “Fixed-term” to match job["type"] or job["duration"] strings.
    - Build personalised emails with:
      - Title, location, pay, type, duration, URL.
      - Short profile line summarising job details.
    - Send emails via Gmail SMTP using app password.

- Verified behaviour:
  - In TEST_MODE:
    - First run with 3 fake jobs:
      - get_new_jobs(): inserts 3 rows into jobs table.
      - Worker logs show:
        - “[worker] TEST_MODE: using 3 fake jobs, 3 new inserted into DB.”
      - Subscriptions for Birmingham/Midlands and London belt get emails:
        - “✅ Email sent to ...”
    - Subsequent test runs with the same fake jobs:
      - get_new_jobs(): 0 new rows (duplicates rejected by UNIQUE).
      - Emails can still be sent based on “new jobs this cycle” or “delta” logic as desired.


6) Current Status vs Original MVP Plan
--------------------------------------
- Scraper engine (Milestone 1):
  - ✅ Implemented and tested against real Amazon jobs.
  - Currently returns 0 jobs when Amazon has none.

- Filtering (Milestone 2):
  - ✅ Implemented within worker:
    - Location: area groups expanded to tokens, matched against job.location.
    - Job type: “Any” or specific types matched via type/duration fields.

- Database & basic alerts (Milestone 3):
  - ✅ SQLite DB in place:
    - jobs table with UNIQUE constraint.
    - get_new_jobs() to identify new jobs.
  - ✅ Verified with test_insert_jobs.py and debug_jobs.py.

- FastAPI web app + subscriptions (Milestone 4):
  - ✅ api.py provides:
    - GET /, POST /subscribe, GET /health.
  - ✅ Users can subscribe with:
    - Email
    - Preferred location string
    - Job type.
  - Subscriptions persisted and visible via debug.

- Worker matching jobs to subscriptions (Milestone 5):
  - ✅ Behaviour implemented in main.py.
  - ✅ Working end-to-end in TEST_MODE:
    - Fake jobs stored in DB.
    - Subscriptions expanded via area groups.
    - Matching logic used to decide who gets which jobs.
    - Emails sent successfully via Gmail.

- Waiting for:
  - Flipping TEST_MODE off and running against real Amazon jobs when they are available again.
  - Optionally adding:
    - last_seen_at column for jobs.
    - Unsubscribe / manage subscriptions endpoints.
    - Better UI (dropdowns, multi-select) instead of free-text location input.
    - Scheduling main.py to run periodically (e.g. Windows Task Scheduler or cron when deployed on a server).


7) Next Logical Steps
---------------------
- When ready for production-like behaviour:
  - Set TEST_MODE = False in main.py.
  - Use headless browser for quiet/background execution if desired.
  - Run main.py periodically (every X minutes/hours) instead of manually.

- UI improvements (optional but nice):
  - Replace free text location with:
    - Multi-select of AREA_GROUP labels
    - Or checkboxes for major areas (Birmingham / Midlands, Leeds / Yorkshire, etc.).
  - Show a confirmation page summarising the user’s choices.

- Long-term:
  - Add other job sources (other retailers, seasonal jobs).
  - Expose an API endpoint to return current jobs for the UI.
  - Build a small Next.js frontend that consumes this backend.
"""
