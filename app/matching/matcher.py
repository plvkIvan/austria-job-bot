from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from rapidfuzz import fuzz

from app.db.models import Job, User

LEVELS = {
    "A1": 1, "A2": 2, "B1": 3,
    "B2": 4, "C1": 5, "C2": 6
}

ANY = {
    "", "-", "any", "beliebig", "будь-який",
    "будь який", "будь яка", "egal", "all"
}

# Synonyms in German, English and Ukrainian.
ALIASES = {
    "lagerarbeiter": "lager",
    "lagermitarbeiter": "lager",
    "lagerhelfer": "lager",
    "warehouse worker": "lager",
    "warehouse assistant": "lager",
    "працівник складу": "lager",
    "робота на складі": "lager",

    "software developer": "softwareentwickler",
    "software engineer": "softwareentwickler",
    "softwareentwicklerin": "softwareentwickler",
    "програміст": "softwareentwickler",
    "розробник": "softwareentwickler",

    "vienna": "wien",
    "відень": "wien",
    "вена": "wien",
}


@dataclass(frozen=True)
class MatchResult:
    score: float
    suitable: bool
    reasons: tuple[str, ...]
    missing_fields: tuple[str, ...]


def normalize(value: str | None) -> str:
    """Normalize text and replace common synonyms."""

    text = unicodedata.normalize(
        "NFKC", value or ""
    ).casefold()

    text = "".join(
        char
        for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )

    text = re.sub(
        r"[^\w]+", " ", text, flags=re.UNICODE
    )

    text = " ".join(text.split())

    for original, replacement in sorted(
        ALIASES.items(),
        key=lambda x: -len(x[0])
    ):
        text = re.sub(
            r"(?<!\w)" + re.escape(original) + r"(?!\w)",
            replacement,
            text
        )

    return text


def employment_type(value: str | None) -> str:
    """Convert employment labels to common values."""

    text = normalize(value)

    if text in ANY:
        return ""

    if text in {
        "vollzeit",
        "full time",
        "fulltime",
        "повна зайнятість"
    }:
        return "full_time"

    if text in {
        "teilzeit",
        "part time",
        "parttime",
        "неповна зайнятість"
    }:
        return "part_time"

    return text


def evaluate_match(
    user: User,
    job: Job,
    threshold: float = 65.0
) -> MatchResult:
    """Evaluate how well a vacancy matches a user.

    Weights:
        Profession: 70 points
        City: 15 points
        Employment: 8 points
        German level: 7 points

    Missing job information receives neutral partial points,
    but is explicitly reported in missing_fields.
    """

    reasons: list[str] = []
    missing: list[str] = []

    query = normalize(user.query)
    title = normalize(job.title)
    description = normalize(job.description)

    if not query or query in ANY:
        return MatchResult(
            0.0,
            False,
            ("No profession in profile",),
            ()
        )

    # 1. Profession matching: max 70 points.

    if not title:
        missing.append("title")
        profession = 0.0

    else:
        similarity = float(
            fuzz.token_set_ratio(query, title)
        )

        if description:
            description_similarity = float(
                fuzz.token_set_ratio(
                    query, description
                )
            ) * 0.8

            similarity = max(
                similarity,
                description_similarity
            )

        profession = 70.0 * similarity / 100.0

    if profession < 35:
        reasons.append(
            "Profession is not a strong match"
        )
    else:
        reasons.append(
            "Profession similarity evaluated"
        )

    score = profession

    # 2. City matching: max 15 points.

    desired_city = normalize(user.city)
    actual_city = normalize(job.city)

    if desired_city and desired_city not in ANY:

        if not actual_city:
            missing.append("city")
            score += 7.5

        elif (
            desired_city in actual_city
            or actual_city in desired_city
        ):
            score += 15
            reasons.append("City matches")

        else:
            return MatchResult(
                0.0,
                False,
                ("Different city",),
                tuple(missing)
            )

    else:
        score += 15

    # 3. Employment: max 8 points.

    desired_employment = employment_type(
        user.employment
    )

    actual_employment = employment_type(
        job.employment
    )

    if desired_employment:

        if not actual_employment:
            missing.append("employment")
            score += 4

        elif desired_employment == actual_employment:
            score += 8
            reasons.append(
                "Employment type matches"
            )

        else:
            return MatchResult(
                0.0,
                False,
                ("Different employment type",),
                tuple(missing)
            )

    else:
        score += 8

    # 4. German level: max 7 points.

    desired_level = (
        user.german_level or ""
    ).upper()

    required_level = (
        job.german_level or ""
    ).upper()

    if required_level in LEVELS:

        if (
            desired_level in LEVELS
            and LEVELS[desired_level]
            < LEVELS[required_level]
        ):
            return MatchResult(
                0.0,
                False,
                ("German level below requirement",),
                tuple(missing)
            )

        if desired_level in LEVELS:
            score += 7
            reasons.append(
                "German level meets requirement"
            )

        else:
            missing.append("user_german_level")

    else:
        missing.append("job_german_level")
        score += 3.5

    # 5. Final score.

    result = round(
        min(100.0, max(0.0, score)),
        1
    )

    return MatchResult(
        score=result,
        suitable=result >= threshold,
        reasons=tuple(reasons),
        missing_fields=tuple(missing)
    )


def match_score(user: User, job: Job) -> float:
    """Backward-compatible function for existing code."""

    return evaluate_match(user, job).score
