"""
Quick helper to list alerts/subscriptions for a given email.

Usage:
  python -m scripts.check_user_alerts you@example.com
"""
import sys

from core.database import get_subscriptions_for_email


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.check_user_alerts <email>")
        sys.exit(1)

    email = sys.argv[1]
    subs = get_subscriptions_for_email(email)
    if not subs:
        print(f"No alerts found for {email}")
        return

    print(f"Found {len(subs)} alert(s) for {email}:")
    for s in subs:
        print(
            f"  id={s.get('id')} "
            f"locations={s.get('preferred_location')} "
            f"job_type={s.get('job_type')} "
            f"created={s.get('created_at')}"
        )


if __name__ == "__main__":
    main()
