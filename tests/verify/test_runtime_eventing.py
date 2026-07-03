"""Tests verifier runtime event adapter."""

from __future__ import annotations

from pathlib import Path

from agent_maintainer.runtime_events.sinks import InMemoryRuntimeEventSink
from agent_maintainer.verify.runtime_eventing import ProfileRuntimeEvents


def test_profile_runtime_events_emit_started_and_finished(tmp_path: Path) -> None:
    """Profile runtime adapter emits compact correlated lifecycle events."""
    sink = InMemoryRuntimeEventSink()
    events = ProfileRuntimeEvents(sink=sink, profile="full", run_id="run-1")

    events.started(tmp_path)
    events.finished(status="pass", exit_code=0, log_dir=tmp_path)

    assert [record["event_name"] for record in sink.records] == [
        "profile.started",
        "profile.finished",
    ]
    assert {record["run_id"] for record in sink.records} == {"run-1"}
    assert sink.records[1]["status"] == "pass"
    assert sink.records[1]["exit_code"] == 0
