"""
Jobs and locations storage re-exports.
"""
from core.db.jobs.jobs_store import (
    get_locations,
    get_all_jobs,
    get_new_jobs,
    get_stats,
)

__all__ = [
    "get_locations",
    "get_all_jobs",
    "get_new_jobs",
    "get_stats",
]
