"""Tests runtime event CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_maintainer.runtime_events import cli


def test_events_summary_text(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Summary command prints compact text."""
    write_event(tmp_path, {"event_name": "command.finished", "status": "pass"})

    status = cli.main(["--events-dir", str(tmp_path), "summary"])

    output = capsys.readouterr().out
    assert status == 0
    assert "Runtime Event Summary" in output
    assert "Events: 1 across 1 file(s)" in output


def test_events_summary_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Summary command prints machine-readable JSON."""
    write_event(tmp_path, {"event_name": "hook.finished", "status": "noop"})

    status = cli.main(["summary", "--events-dir", str(tmp_path), "--format", "json"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["hook_noops"] == 1


def test_events_failures_handles_empty_dir(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Failures command handles empty event directory quietly."""
    status = cli.main(["--events-dir", str(tmp_path), "failures"])

    output = capsys.readouterr().out
    assert status == 0
    assert "Runtime Event Failures" in output
    assert "- none" in output


def write_event(events_dir: Path, record: dict[str, object]) -> None:
    """Write one runtime event JSONL file."""
    event_file = events_dir / "events.jsonl"
    event_file.write_text(f"{json.dumps(record)}\n", encoding="utf-8")
