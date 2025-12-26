import os
import re
import smtplib
import asyncio
import logging
from email.mime.text import MIMEText
from typing import Dict, List

from dotenv import load_dotenv

from app.area_groups import AREA_GROUPS
from core.database import (
    get_active_subscriptions,
    get_all_jobs,
    get_new_jobs,
    init_db,
    create_alert_deliveries,
    mark_alert_deliveries_sent,
    mark_alert_deliveries_failed,
    get_user_by_email,
)
from worker.amazon_engine_us import fetch_jobs

# Load `.env` for local/dev runs (override=True so updates take effect after restart).
load_dotenv(override=True)

# -------- CONFIG --------
CHECK_INTERVAL = 360  # seconds between checks
TEST_MODE = os.getenv("TEST_MODE", "False").lower() == "true"

EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@zone-alerts.com")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
# ------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("worker_us")


def _effective_from() -> str:
    """
    Derive a safe From address:
    - If using Gmail SMTP, force From to authenticated user to avoid rewrites/blocks.
    - Otherwise, default to EMAIL_FROM or EMAIL_USER.
    """
    if "gmail" in SMTP_SERVER.lower() and EMAIL_USER:
        return EMAIL_USER
    return EMAIL_FROM or EMAIL_USER or "noreply@zone-alerts.com"


def send_email(to_email: str, message: str) -> None:
    """Send an email to a single recipient."""
    if not (EMAIL_USER and EMAIL_PASSWORD):
        raise RuntimeError("Email credentials not configured. Set EMAIL_USER and EMAIL_PASSWORD.")

    msg = MIMEText(message)
    msg["Subject"] = "Amazon Job Alert!"
    msg["From"] = _effective_from()
    msg["To"] = to_email

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.sendmail(msg["From"], [to_email], msg.as_string())
    log.info("Email sent", extra={"to": to_email, "from": msg["From"]})


def expand_preferred_locations(raw_pref: str) -> (List[str], bool):
    if not raw_pref:
        return [], False

    tokens: List[str] = []
    parts = [p.strip() for p in raw_pref.split(";") if p.strip()]
    any_mode = False

    for part in parts:
        part_lower = part.lower()

        if part_lower == "any":
            tokens = []
            any_mode = True
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
    return tokens, any_mode


def _location_matches(tokens: List[str], job_location: str) -> bool:
    """
    Safer matching: compare lowercase tokens against normalized job location.
    - Exact token match against split words
    - Fallback substring check to catch multi-word towns
    """
    if not tokens:
        return False

    job_location_lower = (job_location or "").lower()
    job_tokens = set(re.split(r"[^a-z0-9]+", job_location_lower))
    job_tokens = {t for t in job_tokens if t}

    for tok in tokens:
        if tok in job_tokens:
            return True
        if tok in job_location_lower:
            return True
    return False


def job_matches_subscription(job: Dict, sub: Dict) -> bool:
    # Only active subscriptions should match
    if sub.get("active") is not None and not sub.get("active"):
        return False

    loc_pref_raw = sub.get("preferred_location") or ""
    job_type_pref = (sub.get("job_type") or "").strip().lower()

    job_location = (job.get("location") or "").lower()
    job_type_str = f"{job.get('type') or ''} {job.get('duration') or ''}".lower()

    tokens, any_mode = expand_preferred_locations(loc_pref_raw)
    if not any_mode:
        if not tokens:
            return False
        if not _location_matches(tokens, job_location):
            return False

    if job_type_pref and job_type_pref != "any":
        if job_type_pref not in job_type_str:
            return False

    return True


async def run_once() -> int:
    log.info("Checking for jobs...")

    if TEST_MODE:
        jobs = [
            {
                "title": "Warehouse Operative",
                "type": "Full Time",
                "duration": "Fixed-term",
                "pay": "From $19.75",
                "location": "Weston, WI",
                "url": "https://example.com/usjob1",
            },
            {
                "title": "Warehouse Operative",
                "type": "Full Time",
                "duration": "Seasonal",
                "pay": "From $21.10",
                "location": "Charlton, MA",
                "url": "https://example.com/usjob2",
            },
        ]
        candidates = jobs
        log.info("TEST_MODE: using fake jobs", extra={"count": len(jobs)})
    else:
        jobs = await fetch_jobs(headless=True)
        new_jobs = get_new_jobs(jobs)
        candidates = get_all_jobs(limit=200)
        log.info(
            "Fetched jobs: fetched=%d new=%d db_jobs=%d db=%s",
            len(jobs),
            len(new_jobs),
            len(candidates),
            os.getenv("DATABASE_PATH"),
        )

    if not candidates:
        log.info("No jobs available to match this cycle.")
        return 0

    subs = get_active_subscriptions()
    if not subs:
        log.info("No active subscriptions. Nothing to send.")
        return 0

    # email -> list of (subscription_id, job)
    alerts_for_email: Dict[str, List[tuple[int, Dict]]] = {}
    seen_key_for_email: Dict[str, set[str]] = {}

    for job in candidates:
        for sub in subs:
            email = (sub.get("email") or "").strip().lower()
            if not email or "@" not in email:
                continue
            if job_matches_subscription(job, sub):
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

        # Look up user_id for history. If user doesn't exist, skip.
        user = get_user_by_email(email)
        if not user:
            continue
        user_id = int(user["id"])

        # Create delivery history rows (best-effort). Only send jobs not previously delivered.
        sub_to_jobs: Dict[int, List[Dict]] = {}
        for sub_id, job in items:
            sub_to_jobs.setdefault(sub_id, []).append(job)

        sub_to_job_ids: Dict[int, List[int]] = {}
        filtered_items: List[tuple[int, Dict]] = []
        for sub_id, jobs_for_sub in sub_to_jobs.items():
            job_ids = [int(job.get("id")) for job in jobs_for_sub if job.get("id")]
            if not job_ids:
                continue
            inserted_job_ids = create_alert_deliveries(
                user_id=user_id, subscription_id=sub_id, job_ids=job_ids
            )
            if not inserted_job_ids:
                continue
            inserted_set = set(inserted_job_ids)
            sub_to_job_ids[sub_id] = list(inserted_set)
            for job in jobs_for_sub:
                if job.get("id") in inserted_set:
                    filtered_items.append((sub_id, job))

        if not filtered_items:
            continue

        lines: List[str] = []
        lines.append(f"{len(filtered_items)} job(s) found for your preferences.\n")

        for idx, (_sub_id, job) in enumerate(filtered_items, start=1):
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
