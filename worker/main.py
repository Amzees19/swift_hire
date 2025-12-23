import asyncio
import os
import smtplib
import logging
from email.mime.text import MIMEText
from typing import Dict, List

from dotenv import load_dotenv

from app.area_groups import AREA_GROUPS
from core.database import (
    create_alert_deliveries,
    get_active_subscriptions,
    get_new_jobs,
    get_user_by_email,
    init_db,
    mark_alert_deliveries_failed,
    mark_alert_deliveries_sent,
)
from worker.amazon_engine import fetch_jobs

# Load `.env` for local/dev runs (override=True so updates take effect after restart).
load_dotenv(override=True)

# -------- CONFIG --------
CHECK_INTERVAL = 40  # seconds between checks
# Default to test mode for UK worker; set TEST_MODE=false in env to scrape real jobs.
TEST_MODE = os.getenv("TEST_MODE", "true").lower() == "true"
HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
EMAIL_FROM = os.getenv("EMAIL_FROM") or EMAIL_USER or "noreply@zone-alerts.com"

# Align From with Gmail auth to avoid rewrites/blocks.
if "gmail" in SMTP_SERVER.lower() and EMAIL_USER:
    EMAIL_FROM = EMAIL_USER
# ------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("worker")


def send_email(to_email: str, message: str) -> None:
    """Send an email to a single recipient."""
    if not (EMAIL_FROM and EMAIL_USER and EMAIL_PASSWORD):
        raise RuntimeError("Email credentials not configured. Set EMAIL_FROM, EMAIL_USER, EMAIL_PASSWORD.")

    msg = MIMEText(message)
    msg["Subject"] = "Amazon Job Alert!"
    msg["From"] = EMAIL_FROM
    msg["To"] = to_email

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_FROM, [to_email], msg.as_string())
    log.info("Email sent", extra={"to": to_email, "from": EMAIL_FROM})


def expand_preferred_locations(raw_pref: str) -> List[str]:
    """
    Convert preferred_location string into a list of location tokens.
    Supports either area group labels or individual locations separated by ';'.
    """
    if not raw_pref:
        return []

    tokens: List[str] = []
    parts = [p.strip() for p in raw_pref.split(";") if p.strip()]

    for part in parts:
        part_lower = part.lower()

        # "Any" means match all locations
        if part_lower == "any":
            tokens = []
            break

        if part in AREA_GROUPS:
            tokens.extend(AREA_GROUPS[part])
            continue

        matched_group = None
        for label, towns in AREA_GROUPS.items():
            if part_lower in label.lower():
                matched_group = label
                break

        if matched_group:
            tokens.extend(AREA_GROUPS[matched_group])
        else:
            tokens.append(part)

    tokens = [t.lower() for t in tokens]
    tokens = list(dict.fromkeys(tokens))
    return tokens


def job_matches_subscription(job: Dict, sub: Dict) -> bool:
    """
    Decide if a job should be sent to this subscriber based on
    preferred locations and job type.
    """
    loc_pref_raw = sub.get("preferred_location") or ""
    job_type_pref = (sub.get("job_type") or "").strip().lower()

    job_location = (job.get("location") or "").lower()
    job_type_str = f"{job.get('type') or ''} {job.get('duration') or ''}".lower()

    tokens = expand_preferred_locations(loc_pref_raw)
    if tokens and not any(tok in job_location for tok in tokens):
        return False

    if job_type_pref and job_type_pref != "any":
        if job_type_pref not in job_type_str:
            return False

    return True


async def run_once() -> int:
    """
    Do one full check:
    - fetch jobs
    - keep only new jobs (when not in TEST_MODE)
    - match new jobs to subscriptions
    - send emails
    Returns number of emails sent.
    """
    log.info("Checking for jobs...")

    if TEST_MODE:
        jobs = [
            {
                "title": "Warehouse Operative",
                "type": "Full Time",
                "duration": "Fixed-term",
                "pay": "From GBP14.30",
                "location": "Coventry, United Kingdom",
                "url": "https://example.com/job1",
            },
            {
                "title": "Warehouse Operative",
                "type": "Full Time",
                "duration": "Fixed-term",
                "pay": "From GBP14.30",
                "location": "Swansea, Wales",
                "url": "https://example.com/job2",
            },
            {
                "title": "Warehouse Operative",
                "type": "Full Time",
                "duration": "Fixed-term",
                "pay": "From GBP15.00",
                "location": "London, United Kingdom",
                "url": "https://example.com/job3",
            },
        ]
        new_jobs = jobs
        log.info("TEST_MODE: using fake jobs", extra={"count": len(jobs)})
    else:
        jobs = await fetch_jobs(headless=HEADLESS)
        new_jobs = get_new_jobs(jobs)
        log.info("Fetched jobs", extra={"fetched": len(jobs), "new": len(new_jobs)})

    if not new_jobs:
        log.info("No new jobs this cycle.")
        return 0

    subs = get_active_subscriptions()
    if not subs:
        log.info("No active subscriptions. Nothing to send.")
        return 0

    # email -> list of (subscription_id, job)
    alerts_for_email: Dict[str, List[tuple[int, Dict]]] = {}
    seen_key_for_email: Dict[str, set[str]] = {}

    for job in new_jobs:
        for sub in subs:
            if job_matches_subscription(job, sub):
                email = (sub.get("email") or "").strip().lower()
                if not email or "@" not in email:
                    continue
                sub_id = int(sub.get("id") or 0)
                if sub_id <= 0:
                    continue
                job_key = f"{job.get('id') or ''}|{job.get('title') or ''}|{job.get('location') or ''}|{job.get('url') or ''}"
                seen_key_for_email.setdefault(email, set())
                if job_key in seen_key_for_email[email]:
                    continue
                seen_key_for_email[email].add(job_key)
                alerts_for_email.setdefault(email, []).append((sub_id, job))

    sent_count = 0
    for email, items in alerts_for_email.items():
        if not items:
            continue

        user = get_user_by_email(email)
        if not user:
            continue
        user_id = int(user["id"])

        sub_to_job_ids: Dict[int, List[int]] = {}
        for sub_id, job in items:
            job_id = job.get("id")
            if not job_id:
                continue
            sub_to_job_ids.setdefault(sub_id, []).append(int(job_id))
        for sub_id, job_ids in sub_to_job_ids.items():
            create_alert_deliveries(user_id=user_id, subscription_id=sub_id, job_ids=job_ids)

        lines: List[str] = []
        lines.append(f"{len(items)} new job(s) found for your preferences.\n")

        for idx, (_sub_id, job) in enumerate(items, start=1):
            lines.append(f"Job {idx}")
            lines.append(f"Title: {job.get('title')}")
            if job.get("type"):
                lines.append(f"Type: {job['type']}")
            if job.get("duration"):
                lines.append(f"Duration: {job['duration']}")
            if job.get("pay"):
                lines.append(f"Pay: {job['pay']}")
            if job.get("location"):
                lines.append(f"Location: {job['location']}")

            summary_parts = [
                job.get("type") or "",
                job.get("duration") or "",
                job.get("pay") or "",
                job.get("location") or "",
            ]
            summary = ", ".join(p for p in summary_parts if p)
            if summary:
                lines.append(f"Profile: {job.get('title')} - {summary}")

            lines.append(f"URL: {job.get('url')}")
            lines.append("")

        body = "\n".join(lines)
        try:
            send_email(email, body)
            sent_count += 1
            for sub_id, job_ids in sub_to_job_ids.items():
                mark_alert_deliveries_sent(subscription_id=sub_id, job_ids=job_ids)
        except Exception as e:
            log.error("Failed to send email", extra={"to": email, "error": str(e)})
            for sub_id, job_ids in sub_to_job_ids.items():
                mark_alert_deliveries_failed(subscription_id=sub_id, job_ids=job_ids, error=str(e))

    log.info("Cycle complete", extra={"sent_emails": sent_count})
    return sent_count


async def main():
    init_db()

    while True:
        try:
            await run_once()
        except Exception as e:
            log.exception("Error during run", extra={"error": str(e)})

        if TEST_MODE:
            break

        log.info("Sleeping", extra={"seconds": CHECK_INTERVAL})
        await asyncio.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
