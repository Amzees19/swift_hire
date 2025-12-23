"""
User-owned alert delivery history.

Jobs are stored globally in the `jobs` table. The `alert_deliveries` table links jobs to users/subscriptions
so that:
  - Deactivation preserves history.
  - Account deletion can wipe all user-related alert history.
"""
from core.db.alerts.deliveries_store import (
    create_alert_deliveries,
    mark_alert_deliveries_sent,
    mark_alert_deliveries_failed,
    get_alert_deliveries_for_user,
    delete_alert_deliveries_for_user,
)

__all__ = [
    "create_alert_deliveries",
    "mark_alert_deliveries_sent",
    "mark_alert_deliveries_failed",
    "get_alert_deliveries_for_user",
    "delete_alert_deliveries_for_user",
]

