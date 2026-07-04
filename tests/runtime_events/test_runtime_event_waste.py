"""Tests cadence waste summaries from runtime events."""

from __future__ import annotations

import json

from agent_maintainer.runtime_events.read import RuntimeEventReadResult
from agent_maintainer.runtime_events.waste import (
    render_waste_text,
    summarize_runtime_waste,
)


def test_waste_summary_detects_heavy_profile_overlap() -> None:
    """Heavy profile overlap is reported without raw event dumps."""
    report = summarize_runtime_waste(
        RuntimeEventReadResult(
            records=[
                {"event_name": "profile.finished", "profile": "full"},
                {"event_name": "profile.finished", "profile": "ci"},
                {"event_name": "profile.finished", "profile": "security"},
            ],
            files_read=1,
        ),
    )

    signals = {signal["signal"] for signal in report.signals}
    assert signals == {"full-ci-overlap", "three-heavy-profiles"}
    text = render_waste_text(report)
    assert "Runtime Event Waste Report" in text
    assert "three-heavy-profiles" in text
    assert json.dumps({"event_name": "profile.finished"}) not in text


def test_waste_summary_detects_repeated_command_failures() -> None:
    """Repeated command failures are summarized by command name only."""
    report = summarize_runtime_waste(
        RuntimeEventReadResult(
            records=[
                {
                    "event_name": "command.finished",
                    "command": "doctor",
                    "status": "fail",
                },
                {
                    "event_name": "command.finished",
                    "command": "doctor",
                    "status": "fail",
                },
            ],
            files_read=1,
        ),
    )

    assert report.signals == [
        {
            "signal": "repeated-command-failure",
            "command": "doctor",
            "count": 2,
            "severity": "warning",
            "message": "doctor failed 2 times in the sampled event window",
        },
    ]


def test_waste_summary_empty_input_reports_no_measured_signals() -> None:
    """Empty runtime event input is quiet but still lists known limitations."""
    report = summarize_runtime_waste(RuntimeEventReadResult())

    assert report.signals == []
    assert "same-state duplication requires verifier fingerprint events" in report.limitations
