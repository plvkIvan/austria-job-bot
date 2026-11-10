from rapidfuzz.fuzz import token_set_ratio
from app.db.models import Job, User

LEVELS = {'A1': 1, 'A2': 2, 'B1': 3, 'B2': 4, 'C1': 5, 'C2': 6}

def match_score(user: User, job: Job) -> float:
    if user.city and job.city and user.city.casefold() not in job.city.casefold():
        return 0.0
    if user.employment not in ('', '-', 'any', 'beliebig', 'будь-який') and job.employment and user.employment != job.employment:
        return 0.0
    if job.german_level in LEVELS and user.german_level in LEVELS and LEVELS[user.german_level] < LEVELS[job.german_level]:
        return 0.0
    return float(token_set_ratio(user.query.casefold(), f"{job.title} {job.description}".casefold()))
