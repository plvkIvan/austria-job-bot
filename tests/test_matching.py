
from app.db.models import Job, User
from app.matching.matcher import evaluate_match, match_score


def test_city_mismatch():
    user = User(query="Lager", city="Wien")

    job = Job(
        source="demo",
        external_id="1",
        title="Lager",
        company="",
        city="Graz",
        url="https://example.com",
    )

    result = evaluate_match(user, job)

    # Profession matches, but location does not.
    assert result.profession_matches is True
    assert result.location_matches is False

    # The job must NOT be sent to this user.
    assert result.should_notify is False

    # The score is informational only.
    assert match_score(user, job) == result.score
