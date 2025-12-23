import pathlib

import pytest

from core.db import schema
from core.db import base
from core.db.jobs import jobs_store


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    """Provide an isolated SQLite DB and patch modules to point at it."""
    db_path = tmp_path / "test_jobs.db"
    # Patch all modules that cache database_path
    monkeypatch.setattr(base, "database_path", db_path, raising=False)
    monkeypatch.setattr(schema, "database_path", db_path, raising=False)
    monkeypatch.setattr(jobs_store, "database_path", db_path, raising=False)

    schema.init_db()
    return db_path


def test_get_new_jobs_deduplicates_on_unique_constraint(temp_db):
    job = {
        "title": "Warehouse Operative",
        "type": "Full Time",
        "duration": "Regular",
        "pay": "Up to £15.00",
        "location": "London, United Kingdom",
        "url": "https://example.com/job/123",
    }
    inserted_first = jobs_store.get_new_jobs([job])
    inserted_second = jobs_store.get_new_jobs([job])

    # First insert should succeed, second should be ignored by UNIQUE constraint
    assert len(inserted_first) == 1
    assert len(inserted_second) == 0

    # DB should only contain one row
    all_jobs = jobs_store.get_all_jobs()
    assert len(all_jobs) == 1
    assert all_jobs[0]["url"] == job["url"]
