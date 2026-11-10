from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from rapidfuzz import fuzz

from app.db.models import Job, User


LEVELS = {
    "A1": 1,
    "A2": 2,
    "B1": 3,
    "B2": 4,
    "C1": 5,
    "C2": 6,
}

ANY = {
    "", "-", "any", "all",
    "beliebig", "egal",
    "будь який", "будь яка", "будь-який",
}

ALIASES = {
    # Warehouse jobs
    "lagerarbeiter": "lager",
    "lagerarbeiterin": "lager",
    "lagermitarbeiter": "lager",
    "lagerhelfer": "lager",
    "warehouse worker": "lager",
    "warehouse assistant": "lager",
    "працівник складу": "lager",
    "робота на складі": "lager",

    # Software development
    "software developer": "softwareentwickler",
    "software engineer": "softwareentwickler",
    "softwareentwicklerin": "softwareentwickler",
    "softwareentwickler": "softwareentwickler",
    "програміст": "softwareentwickler",
    "розробник": "softwareentwickler",

    # Cities
    "vienna": "wien",
    "відень": "wien",
    "вена": "wien",
    "vienna austria": "wien",
}


@dataclass(frozen=True)
class MatchResult:
    score: float
    should_notify: bool
    rating: str
    reasons: tuple[str, ...]
    missing_fields: tuple[str, ...]
    profession_matches: bool
    location_matches: bool

    @property
    def suitable(self) -> bool:
        """Compatibility with earlier code."""
        return self.should_notify


def normalize(value: str | None) -> str:
    text = unicodedata.normalize(
        "NFKC", str(value or "")
    ).casefold()

    text = "".join(
        char
        for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )

    text = re.sub(r"[^\w]+", " ", text)
    text = " ".join(text.split())

    for original, replacement in sorted(
        ALIASES.items(),
        key=lambda item: -len(item[0]),
    ):
        text = re.sub(
            r"(?<!\w)" + re.escape(original) + r"(?!\w)",
            replacement,
            text,
        )

    return text


def employment_type(value: str | None) -> str:
    text = normalize(value)

    if text in ANY:
        return ""

    if text in {
        "vollzeit", "full time", "fulltime",
        "повна зайнятість",
    }:
        return "full_time"

    if text in {
        "teilzeit", "part time", "parttime",
        "неповна зайнятість",
    }:
        return "part_time"

    return text


def profession_similarity(
    query: str | None,
    title: str | None,
) -> float:
    """Similarity between requested profession and job title."""

    requested = normalize(query)
    actual = normalize(title)

    if not requested or requested in ANY or not actual:
        return 0.0

    if requested == actual:
        return 100.0

    return float(
        fuzz.token_set_ratio(requested, actual)
    )


def profession_matches(
    query: str | None,
    title: str | None,
    minimum_similarity: float = 65.0,
) -> bool:
    """Profession must match the job title.

    A description alone cannot qualify an unrelated title.
    """
    similarity = profession_similarity(query, title)

    return similarity >= minimum_similarity


def location_matches(
    desired_city: str | None,
    actual_city: str | None,
) -> bool:
    """Exact city matching, without guessing a travel radius."""

    desired = normalize(desired_city)
    actual = normalize(actual_city)

    if desired in ANY:
        return True

    if not actual:
        return False

    if desired == actual:
        return True

    # Allows "Wien" to match "Wien, Österreich".
    # Does not match "Wiener Neustadt".
    return bool(
        re.search(
            r"(?<!\w)" + re.escape(desired) + r"(?!\w)",
            actual,
        )
    )


def rating_for_score(score: float) -> str:
    """Information label, not a notification filter."""

    if score >= 80:
        return "high"

    if score >= 60:
        return "good"

    if score >= 40:
        return "partial"

    return "low"


def evaluate_match(
    user: User,
    job: Job,
    threshold: float = 65.0,
) -> MatchResult:
    """Evaluate a job against the user's profile.

    IMPORTANT:
    `threshold` is retained for backwards compatibility.
    It no longer controls notification eligibility.

    Notification eligibility:
        profession_matches AND location_matches

    Informational score:
        Profession: 70 points
        Location: 15 points
        Employment: 8 points
        German: 7 points

    Missing optional information receives partial points,
    but is reported explicitly.
    """

    reasons: list[str] = []
    missing: list[str] = []

    query = getattr(user, "query", "") or ""
    city = getattr(user, "city", "") or ""
    employment = getattr(user, "employment", "") or ""

    job_title = getattr(job, "title", "") or ""
    job_city = getattr(job, "city", "") or ""
    job_employment = getattr(job, "employment", "") or ""

    user_german = (
        getattr(user, "german_level", "") or ""
    ).upper()

    job_german = (
        getattr(job, "german_level", "") or ""
    ).upper()

    if not job_title:
        missing.append("title")

    if not job_city:
        missing.append("city")

    if not job_employment:
        missing.append("employment")

    if not job_german:
        missing.append("job_german_level")

    if not user_german:
        missing.append("user_german_level")

    # ---------------------------------
    # 1. Profession: mandatory criterion
    # ---------------------------------

    similarity = profession_similarity(
        query, job_title
    )

    job_profession_matches = profession_matches(
        query, job_title
    )

    profession_points = 70.0 * similarity / 100.0

    if job_profession_matches:
        reasons.append("profession_matches")
    else:
        reasons.append("profession_mismatch")

    # ---------------------------------
    # 2. Location: mandatory criterion
    # ---------------------------------

    job_location_matches = location_matches(
        city, job_city
    )

    desired_city = normalize(city)

    if desired_city in ANY:
        location_points = 15.0
        reasons.append("location_unrestricted")

    elif job_location_matches:
        location_points = 15.0
        reasons.append("location_matches")

    else:
        location_points = 0.0

        if not job_city:
            reasons.append("location_unknown")
        else:
            reasons.append("location_mismatch")

    # ---------------------------------
    # 3. Employment: informational only
    # ---------------------------------

    desired_employment = employment_type(
        employment
    )

    actual_employment = employment_type(
        job_employment
    )

    employment_penalty = 0.0

    if not desired_employment:
        employment_points = 8.0

    elif not actual_employment:
        employment_points = 4.0
        reasons.append("employment_unknown")

    elif desired_employment == actual_employment:
        employment_points = 8.0
        reasons.append("employment_matches")

    else:
        employment_points = 0.0
        employment_penalty = 25.0
        reasons.append("employment_mismatch")

    # ---------------------------------
    # 4. German: informational only
    # ---------------------------------

    german_penalty = 0.0

    if job_german not in LEVELS:
        german_points = 3.5
        reasons.append("german_requirement_unknown")

    elif user_german not in LEVELS:
        german_points = 0.0
        reasons.append("user_german_unknown")

    elif LEVELS[user_german] >= LEVELS[job_german]:
        german_points = 7.0
        reasons.append("german_matches")

    else:
        german_points = 0.0
        german_penalty = 35.0
        reasons.append("german_below_requirement")

    # ---------------------------------
    # 5. Informational score
    # ---------------------------------

    score = (
        profession_points
        + location_points
        + employment_points
        + german_points
        - employment_penalty
        - german_penalty
    )

    score = round(
        max(0.0, min(100.0, score)),
        1,
    )

    # Only these TWO criteria decide notification.
    should_notify = (
        job_profession_matches
        and job_location_matches
    )

    return MatchResult(
        score=score,
        should_notify=should_notify,
        rating=rating_for_score(score),
        reasons=tuple(reasons),
        missing_fields=tuple(dict.fromkeys(missing)),
        profession_matches=job_profession_matches,
        location_matches=job_location_matches,
    )


def match_score(user: User, job: Job) -> float:
    """Old interface, kept for existing code."""

    return evaluate_match(user, job).score


def should_notify_user(user: User, job: Job) -> bool:
    """Use this function in the future notification service."""

    return evaluate_match(user, job).should_notify
