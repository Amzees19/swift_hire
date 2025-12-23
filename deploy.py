# Here’s a practical “as free as it gets” path for a hobby launch:

# Host the API free-tier: Deploy the FastAPI app on a free platform that allows background tasks or cron-like jobs. Options:
# Render free web service (FastAPI) + separate free “cron job” (for the worker) hitting an HTTP endpoint that triggers scraping (if allowed), or run the worker as a Background Worker (their free tier has monthly limits—watch usage).
# Fly.io free VM (256MB) to run both uvicorn and the worker process via fly scale count 1. Free credits may cover light hobby use; set processes for web and worker.
# Railway free plan can run the API; the worker would need a separate service and careful idle limits.
# Database: Keep SQLite in the repo directory. Most free hosts persist the app disk; just ensure the volume is on a persistent disk (Render: use a persistent disk; Fly: use a volume). Back up jobs.db locally before deploy. If disk isn’t reliable, switch to a free-tier Postgres (Neon/Render free) and map tables there.
# Email (must be free-ish):
# Use Gmail SMTP with an App Password (personal Gmail + 2FA) for low-volume sends; set EMAIL_USER and EMAIL_PASSWORD (app password), SMTP_SERVER=smtp.gmail.com, SMTP_PORT=587. Keep volume tiny to avoid blocks.
# Or try a free transactional tier (Mailgun/Sender/Postmark trial). Put creds in env vars; never commit.
# Turn off test mode: In worker/main.py, set TEST_MODE = False. For worker/main_us.py, set env TEST_MODE=false. Without this, only fake jobs send.
# Secure cookies for HTTPS: In app/auth_utils.py and app/security.py, set secure=True on cookies once you’re on HTTPS.
# Playwright browser install: On the host, run python -m playwright install chromium (needed for real scraping). If the free host blocks it, consider moving scraping to a small VM (free-tier Fly) and keep the API on Render, or run the worker locally on a schedule.
# Environment vars to set in the host dashboard:
# Admin: ADMIN_EMAIL, ADMIN_PASSWORD.
# SMTP: EMAIL_USER, EMAIL_PASSWORD, EMAIL_FROM (optional), SMTP_SERVER, SMTP_PORT.
# PUBLIC_BASE_URL=https://your-hostname.
# Run commands on host:
# API: python -m uvicorn app.api:app --host 0.0.0.0 --port $PORT.
# Worker: python -m worker.main (UK) and/or python -m worker.main_us.
# Minimal pre-flight:
# Install deps: pip install -r requirements.txt and python -m playwright install chromium.
# Run python -m pytest locally.
# Smoke-test locally with your Gmail creds: signup, email verification, dashboard, worker sends an alert in live mode.
# Cheap fallback if free hosts block scraping:
# Run API on Render free tier; run worker on Fly free VM (or locally on a spare machine) with SSH/cron.
# Monitoring: Check /health, tail logs for SMTP errors, and back up jobs.db periodically.
# If you want, I can change TEST_MODE to false, add secure=True on cookies, and generate a requirements.txt to deploy.


