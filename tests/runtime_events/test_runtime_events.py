"""Tests runtime event foundation."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.runtime_events.models import RuntimeEvent
from agent_maintainer.runtime_events.redaction import (
    OMITTED_RAW_VALUE,
    REDACTED,
)
from agent_maintainer.runtime_events.sinks import (
    InMemoryRuntimeEventSink,
    JsonlRuntimeEventSink,
    make_runtime_event_sink,
)

EVENT_DURATION_MS = 123
EVENT_STREAM_ID = "run-1"


# docsync:evidence.start evidence.runtime_events.foundation
def test_runtime_event_record_is_compact_and_sanitized() -> None:
    """Serialized events include stable fields and sanitized attributes."""
    event = RuntimeEvent(
        "check.failed",
        severity="error",
        timestamp=datetime(2026, 7, 3, 20, 30, tzinfo=UTC),
        command="verify",
        profile="precommit",
        run_id="run-1",
        check="pyright",
        status="fail",
        duration_ms=EVENT_DURATION_MS,
        exit_code=1,
        attributes={
            "artifact": ".verify-logs/runs/run-1/pyright.log",
            "stderr": "huge raw transcript",
            "token": "sk-secret-value-that-should-not-appear",
            "message": "Bearer abcdefghijklmnopqrstuvwxyz",
        },
    )

    record = event.to_record()

    assert record["schema_version"] == 1
    assert record["event_name"] == "check.failed"
    assert record["timestamp"] == "2026-07-03T20:30:00Z"
    assert record["severity"] == "error"
    assert record["command"] == "verify"
    assert record["profile"] == "precommit"
    assert record["run_id"] == "run-1"
    assert record["check"] == "pyright"
    assert record["status"] == "fail"
    assert record["duration_ms"] == EVENT_DURATION_MS
    assert record["exit_code"] == 1
    assert record["attributes"]["artifact"] == ".verify-logs/runs/run-1/pyright.log"
    assert record["attributes"]["stderr"] == OMITTED_RAW_VALUE
    assert record["attributes"]["token"] == REDACTED
    assert "abcdefghijklmnopqrstuvwxyz" not in record["attributes"]["message"]


# docsync:evidence.end evidence.runtime_events.foundation


def test_runtime_event_record_normalizes_naive_timestamp_to_utc() -> None:
    """Naive timestamps serialize as UTC runtime events."""
    event = RuntimeEvent(
        "profile.started",
        timestamp=datetime(2026, 7, 3, 20, 30),
    )

    assert event.to_record()["timestamp"] == "2026-07-03T20:30:00Z"


def test_runtime_event_record_truncates_long_attribute_text() -> None:
    """Long runtime event attributes are bounded."""
    event = RuntimeEvent("profile.finished", attributes={"message": "a" * 600})

    assert event.to_record()["attributes"]["message"].endswith("...[truncated]")


def test_in_memory_sink_keeps_serialized_records() -> None:
    """Test sink stores event records without touching filesystem."""
    sink = InMemoryRuntimeEventSink()

    sink.emit(RuntimeEvent("profile.started", command="verify", profile="fast"))

    assert sink.records[0]["event_name"] == "profile.started"
    assert sink.records[0]["command"] == "verify"


def test_jsonl_sink_writes_events_and_filters_by_level(tmp_path: Path) -> None:
    """JSONL sink writes allowed events and filters low-severity events."""
    sink = JsonlRuntimeEventSink.create(
        tmp_path,
        history_limit=10,
        min_level="warning",
        stream_id=EVENT_STREAM_ID,
    )

    sink.emit(RuntimeEvent("profile.started", severity="info"))
    sink.emit(RuntimeEvent("profile.finished", severity="warning", status="pass"))

    records = _read_jsonl(tmp_path / f"{EVENT_STREAM_ID}.jsonl")
    assert [record["event_name"] for record in records] == ["profile.finished"]


def test_jsonl_sink_can_include_debug_when_enabled(tmp_path: Path) -> None:
    """Debug events are omitted unless explicitly enabled."""
    sink = JsonlRuntimeEventSink.create(
        tmp_path,
        history_limit=10,
        min_level="debug",
        include_debug=True,
        stream_id="debug-run",
    )

    sink.emit(RuntimeEvent("command.debug", severity="debug"))

    assert _read_jsonl(tmp_path / "debug-run.jsonl")[0]["event_name"] == "command.debug"


def test_jsonl_sink_retains_newest_event_files(tmp_path: Path) -> None:
    """Retention prunes older JSONL files deterministically."""
    for index in range(4):
        event_file = tmp_path / f"old-{index}.jsonl"
        event_file.write_text("{}\n", encoding="utf-8")
        os.utime(event_file, (index, index))

    JsonlRuntimeEventSink.create(tmp_path, history_limit=2, stream_id="new")

    assert sorted(path.name for path in tmp_path.glob("*.jsonl")) == [
        "old-2.jsonl",
        "old-3.jsonl",
    ]


def test_runtime_event_sink_disabled_by_default(tmp_path: Path) -> None:
    """Runtime events stay no-op unless configured."""
    sink = make_runtime_event_sink(MaintainerConfig(runtime_events_dir=str(tmp_path)))

    sink.emit(RuntimeEvent("profile.started"))

    assert not tuple(tmp_path.glob("*.jsonl"))


def test_jsonl_sink_write_errors_do_not_raise(tmp_path: Path) -> None:
    """Writer errors stay local and do not mask caller behavior."""
    sink = JsonlRuntimeEventSink(
        path=tmp_path,
        history_limit=1,
    )

    sink.emit(RuntimeEvent("profile.started"))

    assert sink.last_error


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
