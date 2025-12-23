"""
Send (or simulate) alerts for existing jobs to existing subscriptions.

This is a debug helper that reads jobs/subscriptions from the DB, matches them,
and prints the "would send" messages. It does NOT send real email.

Usage:
  python -m scripts.send_fake_alerts           # all subscribers
  python -m scripts.send_fake_alerts --email user@example.com  # single user
"""
from __future__ import annotations

import argparse
from typing import Dict, List

from core.database import get_active_subscriptions, get_all_jobs

# Reuse the matching logic from the worker (simplified copy)
AREA_GROUPS = {
    "Birmingham / Midlands": [
        "Birmingham",
        "Rugeley",
        "Coalville",
        "Daventry",
        "Coventry",
        "Rugby",
        "Hinckley",
        "Redditch",
        "Stoke-on-Trent",
        "Wednesbury",
        "Mansfield",
        "Eastwood",
        "Kegworth",
        "Northampton",
        "Banbury",
        "Burton-on-Trent",
    ],
    "Manchester / North West": [
        "Manchester",
        "Warrington",
        "Bolton",
        "Haydock",
        "Rochdale",
        "Carlisle",
        "Stoke-on-Trent",
    ],
    "Leeds / Yorkshire": [
        "Leeds",
        "Doncaster",
        "Wakefield",
        "Sheffield",
        "Hull",
        "North Ferriby",
    ],
    "Newcastle / North East": [
        "Newcastle upon Tyne",
        "Gateshead",
        "Durham",
        "Sunderland",
        "Darlington",
        "Billingham",
    ],
    "London (inner)": [
        "London",
        "Barking",
        "Croydon",
        "Enfield",
        "Bexley",
        "Neasden",
        "Orpington",
    ],
    "London commuter belt / South East": [
        "Tilbury",
        "Dartford",
        "Rochester",
        "Aylesford",
        "Harlow",
        "Grays",
        "Weybridge",
    ],
    "East of England": [
        "Bedford",
        "Milton Keynes",
        "Ridgmont",
        "Dunstable",
        "Peterborough",
        "Norwich",
        "Ipswich",
        "Cambridge",
    ],
    "South West": [
        "Bristol",
        "Swindon",
        "Exeter",
        "Plymouth",
    ],
    "South Wales": [
        "Cardiff",
        "Newport",
        "Port Talbot",
        "Swansea",
        "Garden City",
    ],
    "Glasgow / Edinburgh": [
        "Glasgow",
        "Edinburgh",
        "Dunfermline",
        "Bathgate",
        "Dundee",
    ],
    "Northern Ireland": [
        "Belfast",
        "Portadown",
    ],
}


def expand_preferred_locations(raw_pref: str) -> List[str]:
    if not raw_pref:
        return []
    tokens: List[str] = []
    parts = [p.strip() for p in raw_pref.split(";") if p.strip()]

    for part in parts:
        lower = part.lower()
        if part in AREA_GROUPS:
            tokens.extend(AREA_GROUPS[part])
            continue
        matched = None
        for label, towns in AREA_GROUPS.items():
            if lower in label.lower():
                matched = label
                break
        if matched:
            tokens.extend(AREA_GROUPS[matched])
        else:
            tokens.append(part)

    tokens = [t.lower() for t in tokens]
    tokens = list(dict.fromkeys(tokens))
    return tokens


def job_matches_subscription(job: Dict, sub: Dict) -> bool:
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


def main():
    parser = argparse.ArgumentParser(description="Simulate sending alerts based on existing jobs.")
    parser.add_argument("--email", help="Only process this subscriber email", default=None)
    parser.add_argument("--limit", type=int, help="Limit number of jobs to consider", default=100)
    args = parser.parse_args()

    jobs = get_all_jobs(limit=args.limit)
    subs = get_active_subscriptions()
    if args.email:
        subs = [s for s in subs if s.get("email") and s["email"].lower() == args.email.lower()]

    if not subs:
        print("No subscriptions found for criteria.")
        return

    alerts_for_email: Dict[str, List[Dict]] = {}

    for job in jobs:
        for sub in subs:
            if job_matches_subscription(job, sub):
                email = sub["email"]
                alerts_for_email.setdefault(email, []).append(job)

    if not alerts_for_email:
        print("No matching jobs for any subscriber.")
        return

    for email, jobs_for_email in alerts_for_email.items():
        print(f"\n=== Alerts for {email} ({len(jobs_for_email)} job(s)) ===")
        for idx, job in enumerate(jobs_for_email, start=1):
            print(f"Job {idx}: {job.get('title')} – {job.get('location')} ({job.get('type')} {job.get('duration')})")
            if job.get("pay"):
                print(f"  Pay: {job['pay']}")
            if job.get("url"):
                print(f"  URL: {job['url']}")


if __name__ == "__main__":
    main()
