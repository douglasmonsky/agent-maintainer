"""Tests runtime event summary rendering."""

from __future__ import annotations

import json

from agent_maintainer.runtime_events.read import RuntimeEventReadResult
from agent_maintainer.runtime_events.summary import (
    render_summary_text,
    summarize_runtime_events,
)

EVENT_RECORD_COUNT = 5


def test_summary_counts_core_dogfood_events() -> None:
    """Summary counts fresh, reused, no-op, and failure signals."""
    summary = summarize_runtime_events(RuntimeEventReadResult(records=event_records()))

    assert summary.total_events == EVENT_RECORD_COUNT
    assert summary.fresh_runs == 1
    assert summary.reused_runs == 1
    assert summary.hook_noops == 1
    assert len(summary.failures) == 1


def test_summary_ranks_slow_checks() -> None:
    """Summary orders check durations descending."""
    summary = summarize_runtime_events(RuntimeEventReadResult(records=event_records()))

    assert [row["check"] for row in summary.slow_checks] == ["pytest", "ruff"]


def test_summary_text_stays_compact() -> None:
    """Rendered text avoids raw JSONL dumps."""
    text = render_summary_text(
        summarize_runtime_events(RuntimeEventReadResult(records=event_records())),
    )

    assert "Runtime Event Summary" in text
    assert "Failures/exceptions: 1" in text
    assert "command=verify" in text
    assert "{" not in text
    assert json.dumps(event_records()[0]) not in text


def event_records() -> list[dict[str, object]]:
    """Return representative runtime event records."""
    return [
        {"event_name": "verifier.fresh"},
        {"event_name": "verifier.reused"},
        {"event_name": "hook.finished", "status": "noop"},
        {
            "event_name": "check.finished",
            "status": "pass",
            "check": "ruff",
            "duration_ms": 25,
        },
        {
            "event_name": "check.finished",
            "command": "verify",
            "severity": "error",
            "status": "fail",
            "check": "pytest",
            "duration_ms": 200,
        },
    ]
