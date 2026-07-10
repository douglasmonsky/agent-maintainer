"""Tests for local runtime event export contracts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_maintainer.runtime_events import cli


def test_events_export_jsonl_preserves_source_location(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """JSONL export includes source file and line for each event."""
    write_event(tmp_path, {"event_name": "check.finished", "status": "pass"})

    status = cli.main(["--events-dir", str(tmp_path), "export", "--format", "jsonl"])

    assert status == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["event_name"] == "check.finished"
    assert payload["source_file"] == "events.jsonl"
    assert payload["source_line"] == 1


def test_events_export_otel_json_is_local_shape(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """OTel JSON export uses local OpenTelemetry-shaped JSON only."""
    write_event(tmp_path, {"event_name": "hook.finished", "status": "noop"})

    status = cli.main(["export", "--events-dir", str(tmp_path), "--format", "otel-json"])

    assert status == 0
    payload = json.loads(capsys.readouterr().out)
    spans = payload["resourceSpans"][0]["scopeSpans"][0]["spans"]
    assert spans[0]["name"] == "hook.finished"
    assert {"key": "source.line", "value": {"intValue": 1}} in spans[0]["attributes"]


def write_event(events_dir: Path, payload: dict[str, object]) -> None:
    """Write one runtime event."""
    events_dir.mkdir(parents=True, exist_ok=True)
    (events_dir / "events.jsonl").write_text(json.dumps(payload) + "\n", encoding="utf-8")
