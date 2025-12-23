import types
import asyncio

import pytest

import worker.main_us as worker_us


@pytest.fixture(autouse=True)
def restore_test_mode():
    """Reset TEST_MODE after each test."""
    original = worker_us.TEST_MODE
    yield
    worker_us.TEST_MODE = original


def _make_job(title="Job1", location="Rochester, NY", type_="Full Time"):
    return {
        "id": 1,
        "title": title,
        "type": type_,
        "duration": "Regular",
        "pay": "Up to $20.00",
        "location": location,
        "url": f"https://example.com/{title}",
    }


def test_run_once_sends_emails_to_matching_subs(monkeypatch):
    jobs = [_make_job(title="Job1", location="Rochester, NY")]
    subs = [
        {"id": 1, "email": "user1@example.com", "preferred_location": "Rochester, NY", "job_type": "Any", "active": 1},
        {"id": 2, "email": "user2@example.com", "preferred_location": "London", "job_type": "Any", "active": 1},
    ]
    sent = []
    deliveries = []

    monkeypatch.setattr(worker_us, "TEST_MODE", False)
    async def _fetch_jobs(headless=True):
        return jobs

    monkeypatch.setattr(worker_us, "fetch_jobs", _fetch_jobs)
    monkeypatch.setattr(worker_us, "get_new_jobs", lambda _jobs: _jobs)
    monkeypatch.setattr(worker_us, "get_active_subscriptions", lambda: subs)
    monkeypatch.setattr(worker_us, "send_email", lambda to, body: sent.append((to, body)))
    monkeypatch.setattr(worker_us, "get_user_by_email", lambda email: {"id": 10, "email": email})
    monkeypatch.setattr(worker_us, "create_alert_deliveries", lambda **kw: deliveries.append(("create", kw)))
    monkeypatch.setattr(worker_us, "mark_alert_deliveries_sent", lambda **kw: deliveries.append(("sent", kw)))
    monkeypatch.setattr(worker_us, "mark_alert_deliveries_failed", lambda **kw: deliveries.append(("failed", kw)))

    sent_count = asyncio.run(worker_us.run_once())

    assert sent_count == 1
    assert len(sent) == 1
    assert sent[0][0] == "user1@example.com"
    assert isinstance(sent[0][1], str) and sent[0][1]
    assert any(kind == "create" for kind, _ in deliveries)
    assert any(kind == "sent" for kind, _ in deliveries)


def test_run_once_no_matches_sends_no_email(monkeypatch):
    jobs = [_make_job(title="Job1", location="London, United Kingdom")]
    subs = [{"id": 1, "email": "user1@example.com", "preferred_location": "Rochester, NY", "job_type": "Any", "active": 1}]
    sent = []

    monkeypatch.setattr(worker_us, "TEST_MODE", False)
    async def _fetch_jobs(headless=True):
        return jobs

    monkeypatch.setattr(worker_us, "fetch_jobs", _fetch_jobs)
    monkeypatch.setattr(worker_us, "get_new_jobs", lambda _jobs: _jobs)
    monkeypatch.setattr(worker_us, "get_active_subscriptions", lambda: subs)
    monkeypatch.setattr(worker_us, "send_email", lambda to, body: sent.append((to, body)))
    monkeypatch.setattr(worker_us, "get_user_by_email", lambda email: {"id": 10, "email": email})

    sent_count = asyncio.run(worker_us.run_once())

    assert sent_count == 0
    assert sent == []


def test_run_once_logs_and_skips_on_smtp_failure(monkeypatch, caplog):
    jobs = [_make_job(title="Job1", location="Rochester, NY")]
    subs = [{"id": 1, "email": "user1@example.com", "preferred_location": "Rochester, NY", "job_type": "Any", "active": 1}]

    monkeypatch.setattr(worker_us, "TEST_MODE", False)
    async def _fetch_jobs(headless=True):
        return jobs

    monkeypatch.setattr(worker_us, "fetch_jobs", _fetch_jobs)
    monkeypatch.setattr(worker_us, "get_new_jobs", lambda _jobs: _jobs)
    monkeypatch.setattr(worker_us, "get_active_subscriptions", lambda: subs)
    monkeypatch.setattr(worker_us, "get_user_by_email", lambda email: {"id": 10, "email": email})
    monkeypatch.setattr(worker_us, "create_alert_deliveries", lambda **kw: None)
    monkeypatch.setattr(worker_us, "mark_alert_deliveries_sent", lambda **kw: None)
    monkeypatch.setattr(worker_us, "mark_alert_deliveries_failed", lambda **kw: None)

    def _fail(*args, **kwargs):
        raise RuntimeError("SMTP down")

    monkeypatch.setattr(worker_us, "send_email", _fail)

    with caplog.at_level("ERROR"):
        sent_count = asyncio.run(worker_us.run_once())
        assert any("Failed to send email" in rec.message for rec in caplog.records)

    # Even with failures, the worker should not crash and should report zero sent
    assert sent_count == 0
