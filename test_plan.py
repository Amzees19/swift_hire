# Plan for tests

# Structure
# Create a tests/ folder at the repo root.
# Use pytest as the primary runner; keep tests simple (no external services).
# Add small unit tests for:
# Location matching (UK and US workers) given subscription prefs.
# Email/validation helpers (server-side email/password validators).
# DB access where feasible with an in-memory sqlite DB or a temp copy.
# Core targets
# Matching logic:
# worker.main_us.job_matches_subscription and _location_matches with cases: Any, exact town, area group, empty prefs, and job_type filtering.
# app.routes.my_alerts.job_matches_subscription similarly.
# Validation:
# _is_valid_email and _is_valid_password in app/routes/public.py with valid/invalid samples and length/space constraints.
# Password reset tokens:
# core.db.users.password_reset functions: create, expire, single-use, invalid token cleanup (use in-memory sqlite).
# Security headers middleware:
# app/api.py middleware sets expected headers on a test client GET.
# Test setup
# Use pytest fixtures:
# client fixture with fastapi.testclient.TestClient(app) to hit routes for header checks.
# temp_db fixture that copies jobs.db to a temp location or uses sqlite3.connect(":memory:") with schema init (if schema easily applied); environment variable override to point DB to temp.
# Markers:
# @pytest.mark.unit for pure logic tests; @pytest.mark.integration for DB-bound ones.
# Tooling
# Add a pytest.ini (or pyproject config) to disable warning noise and set test paths.
# Keep tests ASCII and self-contained; no network.
# Commands to run
# pytest (default: all unit tests).
# pytest -m integration (when you want DB-bound checks).
# Keep test run light so it can be run locally and in CI later.
# If you’re happy with this plan, I’ll scaffold tests/ with fixtures and initial test files for matching, validation, reset tokens, and security headers.


# ########################################
# Here’s a focused list of high-value tests to add so we cover matching, “Any” handling, and security-critical paths before going public:

# Matching / alerts

# Location “Any”: when a user’s preferred_location is “Any”, every job should match regardless of location tokens.
# Tokenized matching: multi-token preference (“Glasgow / Edinburgh”) matches jobs containing either token (case-insensitive), but “Glasgow” should not match “Gloucester”.
# No false positives: jobs outside all preferred tokens do not appear.
# Deactivated subscriptions: inactive subs never receive matches/emails.
# Job type filter: job_type “Full Time” only returns Full Time; job_type “Any” returns all types.
# Duplicate jobs: same job ID inserted twice only yields one match.
# US vs UK engine: ensure the “us” matching respects US test tokens and doesn’t cross-match UK locations.
# Security / auth

# CSRF: POSTs to subscribe/login/reset without a valid CSRF token are rejected (403).
# Admin authz: admin routes reject non-admin or unauthenticated users.
# Rate limiting: login/reset/subscribe beyond the configured limit returns 429.
# Password reset: token is single-use and expires; invalid/used token returns 400/410; does not leak “unknown email”.
# Sessions: deleted/inactive user clears session and forces login.
# Validation

# Email: leading/trailing spaces trimmed; punycode rejected; double dots/user@.example.com rejected; long-but-valid under 254 OK.
# Password: 8–25 chars, letter+digit, no whitespace; rejects longer or space-containing strings; accepts boundary lengths.
# Security headers

# Already have CSP/nosniff/SAMEORIGIN—add a test that the middleware preserves existing headers (e.g., pre-set CSP is not overridden if you choose to keep caller’s value).
# Worker / email delivery

# When matching jobs are found, an email is queued/sent to exactly the subscribed emails; when no matches, no email is sent.
# SMTP failure is logged and does not crash the worker loop.
# Suggested placements

# tests/test_matching_any.py (location/type/active/deactive/duplicate cases).
# tests/test_security_authz.py (CSRF, admin authz, rate limits).
# Extend tests/test_password_reset.py (single-use, expiry, unknown-email).
# Extend tests/test_validation.py (extra email/password edge cases above).
# Extend tests/test_security_headers.py (header preservation).
# Run

# python -m 