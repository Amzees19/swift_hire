from core.database import database_path, get_new_jobs, init_db

# Make sure DB + tables exist
init_db()
print("DB path from database:", database_path.resolve())

fake_jobs = [
    {
        "title": "Warehouse Operative - Coventry",
        "type": "Full Time",
        "duration": "Fixed-term",
        "pay": "From £14.30",
        "location": "Coventry, United Kingdom",
        "url": "https://example.com/job1",
    },
    {
        "title": "Warehouse Operative - Swansea",
        "type": "Full Time",
        "duration": "Fixed-term",
        "pay": "From £14.30",
        "location": "Swansea, Wales",
        "url": "https://example.com/job2",
    },
    {
        "title": "Warehouse Operative - London",
        "type": "Full Time",
        "duration": "Fixed-term",
        "pay": "From £15.00",
        "location": "London, United Kingdom",
        "url": "https://example.com/job3",
    },
]

new_jobs = get_new_jobs(fake_jobs)
print(f"get_new_jobs() returned {len(new_jobs)} new jobs")

