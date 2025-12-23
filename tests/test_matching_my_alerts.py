from app.routes.my_alerts import job_matches_subscription, expand_preferred_locations


def test_expand_tokens_and_any():
    tokens, any_mode = expand_preferred_locations("Any")
    assert any_mode is True
    assert tokens == []

    tokens, any_mode = expand_preferred_locations("Birmingham / Midlands")
    assert any_mode is False
    assert tokens  # should expand to non-empty


def test_job_match_location_and_type():
    job = {"location": "Glasgow, United Kingdom", "type": "Full Time", "duration": "Fixed-term"}
    tokens, any_mode = expand_preferred_locations("Glasgow / Edinburgh")
    assert job_matches_subscription(job, tokens, "full time", any_mode, subscription_active=True)


def test_job_no_match_location():
    job = {"location": "London, United Kingdom", "type": "Full Time", "duration": "Regular"}
    tokens, any_mode = expand_preferred_locations("Manchester")
    assert not job_matches_subscription(job, tokens, "any", any_mode, subscription_active=True)


def test_job_no_match_type():
    job = {"location": "London, United Kingdom", "type": "Part Time", "duration": "Regular"}
    tokens, any_mode = expand_preferred_locations("London")
    assert not job_matches_subscription(job, tokens, "full time", any_mode, subscription_active=True)


def test_job_matches_any_location_flag():
    job = {"location": "Anywhere", "type": "Full Time", "duration": "Regular"}
    tokens, any_mode = expand_preferred_locations("Any")
    assert job_matches_subscription(job, tokens, "any", any_mode, subscription_active=True)


def test_job_does_not_match_partial_word():
    job = {"location": "Gloucester, United Kingdom", "type": "Full Time", "duration": "Regular"}
    tokens, any_mode = expand_preferred_locations("Glasgow")
    assert not job_matches_subscription(job, tokens, "any", any_mode, subscription_active=True)


def test_inactive_subscription_does_not_match():
    job = {"location": "London, United Kingdom", "type": "Full Time", "duration": "Regular"}
    tokens, any_mode = expand_preferred_locations("London")
    assert not job_matches_subscription(job, tokens, "any", any_mode, subscription_active=False)


def test_uk_subscription_does_not_match_us_job():
    job = {"location": "Rochester, NY", "type": "Full Time", "duration": "Regular"}
    tokens, any_mode = expand_preferred_locations("Glasgow / Edinburgh")
    assert not job_matches_subscription(job, tokens, "any", any_mode, subscription_active=True)
