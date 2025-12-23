from worker.main_us import job_matches_subscription, expand_preferred_locations, _location_matches


def test_expand_any():
    tokens, any_mode = expand_preferred_locations("Any")
    assert any_mode is True
    assert tokens == []


def test_expand_area_group_and_specific():
    tokens, any_mode = expand_preferred_locations("Birmingham / Midlands; London")
    assert any_mode is False
    assert "birmingham" in tokens
    assert "london" in tokens or any("london" in t for t in tokens)


def test_location_matches_tokenized():
    job_loc = "Coventry, United Kingdom"
    tokens = ["coventry"]
    assert _location_matches(tokens, job_loc)
    assert not _location_matches(["manchester"], job_loc)


def test_job_matches_any_location():
    job = {"location": "Anywhere", "type": "Full Time", "duration": "Regular"}
    sub = {"preferred_location": "Any", "job_type": "Any"}
    assert job_matches_subscription(job, sub)


def test_job_matches_specific_location_and_type():
    job = {"location": "London, United Kingdom", "type": "Full Time", "duration": "Seasonal"}
    sub = {"preferred_location": "London", "job_type": "Full Time"}
    assert job_matches_subscription(job, sub)


def test_job_does_not_match_wrong_location():
    job = {"location": "London, United Kingdom", "type": "Full Time", "duration": "Seasonal"}
    sub = {"preferred_location": "Manchester", "job_type": "Any"}
    assert not job_matches_subscription(job, sub)


def test_job_does_not_match_wrong_type():
    job = {"location": "London, United Kingdom", "type": "Part Time", "duration": "Regular"}
    sub = {"preferred_location": "London", "job_type": "Full Time"}
    assert not job_matches_subscription(job, sub)


def test_job_type_any_allows_any_type():
    job = {"location": "London, United Kingdom", "type": "Contract", "duration": "Regular"}
    sub = {"preferred_location": "London", "job_type": "Any"}
    assert job_matches_subscription(job, sub)


def test_job_matches_multi_token_case_insensitive():
    job = {"location": "Edinburgh, united kingdom", "type": "Full Time", "duration": "Regular"}
    sub = {"preferred_location": "glasgow / edinburgh", "job_type": "Any"}
    assert job_matches_subscription(job, sub)


def test_job_does_not_match_partial_word():
    job = {"location": "Gloucester, United Kingdom", "type": "Full Time", "duration": "Regular"}
    sub = {"preferred_location": "Glasgow", "job_type": "Any"}
    assert not job_matches_subscription(job, sub)


def test_inactive_subscription_does_not_match():
    job = {"location": "London, United Kingdom", "type": "Full Time", "duration": "Regular"}
    sub = {"preferred_location": "London", "job_type": "Any", "active": 0}
    assert not job_matches_subscription(job, sub)


def test_us_subscription_does_not_match_uk_job():
    job = {"location": "London, United Kingdom", "type": "Full Time", "duration": "Regular"}
    sub = {"preferred_location": "Rochester, NY", "job_type": "Any"}
    assert not job_matches_subscription(job, sub)


def test_us_subscription_matches_us_job():
    job = {"location": "Rochester, NY", "type": "Full Time", "duration": "Regular"}
    sub = {"preferred_location": "Rochester, NY", "job_type": "Any"}
    assert job_matches_subscription(job, sub)
