"""Tests cadence waste summaries from runtime events."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from agent_maintainer.runtime_events.read import RuntimeEventReadResult
from agent_maintainer.runtime_events.waste import (
    render_waste_text,
    summarize_runtime_waste,
)

GENERATED_ARTIFACT_COUNT = 2
FAILED_COMMAND_COUNT = 2


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

    assert len(report.signals) == 1
    signal = report.signals[0]
    assert signal["signal"] == "repeated-command-failure"
    assert signal["command"] == "doctor"
    assert signal["count"] == FAILED_COMMAND_COUNT
    assert signal["severity"] == "warning"
    assert signal["message"] == "doctor failed 2 times in sampled event window"


def test_waste_summary_empty_input_reports_no_measured_signals() -> None:
    """Empty runtime event input is quiet but still lists known limitations."""
    report = summarize_runtime_waste(RuntimeEventReadResult())

    assert report.signals == []
    assert "same-state duplication requires verifier fingerprint events" in report.limitations


def test_waste_summary_detects_generated_artifact_debris(tmp_path: Path) -> None:
    """Generated artifact debris is reported without reading file contents."""
    cache_dir = tmp_path / "src" / "__pycache__"
    cache_dir.mkdir(parents=True)
    (cache_dir / "module.cpython-313.pyc").write_bytes(b"binary cache")
    (tmp_path / "docs" / "Guide 2.md").parent.mkdir()
    (tmp_path / "docs" / "Guide 2.md").write_text("duplicate", encoding="utf-8")

    report = summarize_runtime_waste(RuntimeEventReadResult(), repo_root=tmp_path)

    signal = report.signals[0]
    paths = cast(list[str], signal["paths"])
    assert signal["signal"] == "generated-artifact-debris"
    assert signal["count"] == GENERATED_ARTIFACT_COUNT
    assert "src/__pycache__" in paths
    assert "docs/Guide 2.md" in paths
    text = render_waste_text(report)
    assert "src/__pycache__" in text
    assert "docs/Guide 2.md" in text
    assert "inspect listed paths" in text
    assert "binary cache" not in text
