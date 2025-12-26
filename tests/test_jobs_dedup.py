from core.db.jobs import jobs_store


def test_get_new_jobs_deduplicates_on_unique_constraint():
    job = {
        "title": "Warehouse Operative",
        "type": "Full Time",
        "duration": "Regular",
        "pay": "Up to $15.00",
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
