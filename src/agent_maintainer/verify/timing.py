"""Timing metadata helpers for verifier artifacts."""

from __future__ import annotations

import datetime as dt

from agent_maintainer.models import CheckResult


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
