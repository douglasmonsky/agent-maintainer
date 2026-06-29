"""Scoring fixture for test-intelligence examples."""

ADVANCED_THRESHOLD = 90
PROFICIENT_THRESHOLD = 70


def clamp_score(score: int, maximum: int) -> int:
    """Return score bounded to the rubric range."""

    if score < 0:
        return 0
    return score


def mastery_band(score: int) -> str:
    """Return a simple mastery band."""

    if score >= ADVANCED_THRESHOLD:
        return "advanced"
    if score >= PROFICIENT_THRESHOLD:
        return "proficient"
    return "developing"
