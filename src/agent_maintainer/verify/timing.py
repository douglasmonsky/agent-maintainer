"""Timing metadata helpers for verifier artifacts."""

from __future__ import annotations

import datetime as dt

from agent_maintainer.models import CheckResult

SECONDS_PER_MINUTE = 60
PROFILE_DURATION_HINTS = (
    ("fast", "expected quick edit check"),
    ("precommit", "expected local commit check"),
    ("full", "expected broad local check"),
    ("ci", "expected CI-equivalent check"),
    ("security", "expected security-focused check"),
    ("manual", "expected slow manual check"),
)


def utc_timestamp() -> str:
    """Return stable UTC timestamp for JSON artifacts."""

    return (
        dt.datetime.now(tz=dt.UTC)
        .isoformat(timespec="seconds")
        .replace(
            "+00:00",
            "Z",
        )
    )


def run_timing(results: list[CheckResult]) -> dict[str, object]:
    """Return run-level timing metadata derived from check timestamps."""

    started_at = sorted(result.started_at for result in results if result.started_at)
    ended_at = sorted(result.ended_at for result in results if result.ended_at)
    start = started_at[0] if started_at else ""
    end = ended_at[-1] if ended_at else ""
    return {
        "started_at": start,
        "ended_at": end,
        "duration_seconds": duration_seconds(start, end),
    }


def profile_duration_hint(profile: str) -> str:
    """Return expected duration hint for a verifier profile."""

    for profile_name, hint in PROFILE_DURATION_HINTS:
        if profile == profile_name:
            return hint
    return "expected verifier check"


def format_duration(seconds: float | None) -> str:
    """Return compact human-readable duration text."""

    if seconds is None:
        return "unknown"
    if seconds < SECONDS_PER_MINUTE:
        return f"{seconds:.1f}s"
    minutes = int(seconds // SECONDS_PER_MINUTE)
    remainder = int(seconds % SECONDS_PER_MINUTE)
    return f"{minutes}m {remainder}s"


def duration_seconds(started_at: str, ended_at: str) -> float | None:
    """Return elapsed seconds for two ISO UTC timestamps when parseable."""

    if not started_at or not ended_at:
        return None
    try:
        return parsed_duration_seconds(started_at, ended_at)
    except ValueError:
        return None


def parsed_duration_seconds(started_at: str, ended_at: str) -> float:
    """Return elapsed seconds for parseable ISO UTC timestamps."""

    start = dt.datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    end = dt.datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
    return max(0, (end - start).total_seconds())
