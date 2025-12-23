from core.db import base


def test_database_path_points_to_jobs_db():
    assert base.database_path.name == "jobs.db"
