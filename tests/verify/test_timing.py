"""Tests for verifier timing metadata helpers."""

from __future__ import annotations

from agent_maintainer.models import CheckResult
from agent_maintainer.verify import timing


def test_run_timing_uses_outer_check_bounds() -> None:
    """Run timing spans earliest check start to latest check end."""

    result = timing.run_timing(
        [
            CheckResult(
                "ruff",
                passed=True,
                started_at="2026-06-25T10:00:02Z",
                ended_at="2026-06-25T10:00:04Z",
            ),
            CheckResult(
                "pytest",
                passed=True,
                started_at="2026-06-25T10:00:00Z",
                ended_at="2026-06-25T10:00:05Z",
            ),
        ],
    )

    assert result == {
        "started_at": "2026-06-25T10:00:00Z",
        "ended_at": "2026-06-25T10:00:05Z",
        "duration_seconds": 5.0,
    }


def test_duration_seconds_handles_missing_or_invalid_values() -> None:
    """Unparseable timing data remains nonfatal artifact metadata."""

    assert timing.duration_seconds("", "2026-06-25T10:00:00Z") is None
    assert timing.duration_seconds("not-a-date", "2026-06-25T10:00:00Z") is None
