
from app.db.models import Job, User
from app.matching.matcher import (
    evaluate_match,
    location_matches,
    match_score,
    should_notify_user,
)


def make_user(**overrides):
    data = {
        "query": "Lagerarbeiter",
        "city": "Wien",
        "employment": "vollzeit",
        "german_level": "B2",
    }

    data.update(overrides)
    return User(**data)


def make_job(**overrides):
    data = {
        "source": "demo",
        "external_id": "test-1",
        "title": "Lagermitarbeiter",
        "city": "Wien",
        "url": "https://example.com/job/1",
        "employment": "vollzeit",
        "german_level": "B1",
    }

    data.update(overrides)
    return Job(**data)


def test_perfect_match():
    user = make_user()
    job = make_job()

    result = evaluate_match(user, job)

    assert result.score == 100.0
    assert result.rating == "high"
    assert result.should_notify is True
    assert result.profession_matches is True
    assert result.location_matches is True


def test_low_score_does_not_block_notification():
    """Main business rule."""

    user = make_user(
        german_level="A2",
        employment="teilzeit",
    )

    job = make_job(
        german_level="C1",
        employment="vollzeit",
    )

    result = evaluate_match(user, job)

    assert result.score < 65
    assert result.should_notify is True
    assert result.suitable is True
    assert result.rating in {"low", "partial"}


def test_wrong_city_blocks_notification():
    user = make_user(city="Graz")
    job = make_job(city="Wien")

    result = evaluate_match(user, job)

    assert result.location_matches is False
    assert result.should_notify is False


def test_wrong_profession_blocks_notification():
    user = make_user(query="Java Developer")
    job = make_job(title="Kellner")

    result = evaluate_match(user, job)

    assert result.profession_matches is False
    assert result.should_notify is False


def test_missing_location_blocks_notification():
    user = make_user(city="Wien")
    job = make_job(city="")

    result = evaluate_match(user, job)

    assert result.should_notify is False
    assert "city" in result.missing_fields
    assert "location_unknown" in result.reasons


def test_missing_optional_details_do_not_block():
    user = make_user()

    job = make_job(
        employment="",
        german_level="",
    )

    result = evaluate_match(user, job)

    assert result.should_notify is True
    assert "employment" in result.missing_fields
    assert "job_german_level" in result.missing_fields


def test_ukrainian_and_english_synonyms():
    ukrainian_user = make_user(
        query="працівник складу",
        city="Відень",
    )

    english_user = make_user(
        query="Warehouse worker",
        city="Vienna",
    )

    job = make_job()

    assert should_notify_user(
        ukrainian_user, job
    ) is True

    assert should_notify_user(
        english_user, job
    ) is True


def test_vienna_is_not_wiener_neustadt():
    assert location_matches(
        "Wien", "Wien, Österreich"
    ) is True

    assert location_matches(
        "Wien", "Wiener Neustadt"
    ) is False


def test_score_is_independent_of_notification():
    user = make_user(german_level="A1")
    job = make_job(german_level="C2")

    result = evaluate_match(user, job)

    assert result.score < 65
    assert result.should_notify is True
    assert match_score(user, job) == result.score


def test_unrestricted_city():
    user = make_user(city="")
    job = make_job(city="Graz")

    assert should_notify_user(user, job) is True


def test_threshold_no_longer_blocks():
    user = make_user(german_level="A1")
    job = make_job(german_level="C2")

    result = evaluate_match(
        user,
        job,
        threshold=99.0,
    )

    assert result.score < 99
    assert result.should_notify is True
