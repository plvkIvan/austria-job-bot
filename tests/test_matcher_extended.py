
from app.db.models import Job, User
from app.matching.matcher import (
    evaluate_match,
    match_score,
)


def make_job(**overrides):
    data = {
        "source": "demo",
        "external_id": "1",
        "title": "Lagerarbeiter",
        "city": "Wien",
        "url": "https://example.com/job/1",
    }

    data.update(overrides)
    return Job(**data)


def test_exact_match_is_high():
    user = User(
        query="Lagerarbeiter",
        city="Wien",
        employment="vollzeit",
        german_level="B2",
    )

    job = make_job(
        employment="vollzeit",
        german_level="B1",
    )

    result = evaluate_match(user, job)

    assert result.score == 100
    assert result.suitable


def test_synonyms_and_three_languages():
    user_en = User(
        query="Warehouse worker",
        city="Vienna",
    )

    user_uk = User(
        query="працівник складу",
        city="Відень",
    )

    assert evaluate_match(
        user_en, make_job()
    ).score >= 90

    assert evaluate_match(
        user_uk, make_job()
    ).suitable


def test_mismatched_city_rejected():
    user = User(
        query="Lagerarbeiter",
        city="Graz",
    )

    result = evaluate_match(user, make_job())

    assert result.score == 0
    assert not result.suitable


def test_mismatched_employment_rejected():
    user = User(
        query="Lagerarbeiter",
        employment="teilzeit",
    )

    job = make_job(employment="vollzeit")

    result = evaluate_match(user, job)

    assert result.score == 0


def test_german_requirement_rejected():
    user = User(
        query="Lagerarbeiter",
        german_level="A2",
    )

    job = make_job(german_level="B2")

    result = evaluate_match(user, job)

    assert result.score == 0


def test_missing_fields_are_explicit_not_assumed():
    user = User(
        query="Lagerarbeiter",
        city="Wien",
        employment="vollzeit",
    )

    job = make_job(
        city="",
        employment="",
        german_level="",
    )

    result = evaluate_match(user, job)

    assert "city" in result.missing_fields
    assert "employment" in result.missing_fields
    assert "job_german_level" in result.missing_fields

    assert 0 < result.score < 100


def test_unrelated_title_is_not_recommended():
    user = User(
        query="Java Developer",
        city="Wien",
    )

    job = make_job(title="Kellner")

    result = evaluate_match(user, job)

    assert not result.suitable


def test_existing_match_score_api_still_works():
    user = User(
        query="Lagerarbeiter",
        city="Wien",
    )

    assert match_score(
        user, make_job()
    ) >= 90
