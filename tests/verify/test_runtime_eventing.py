"""Tests verifier runtime event adapter."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from agent_maintainer.runtime_events.sinks import InMemoryRuntimeEventSink
from agent_maintainer.verify import runtime_eventing

EXPECTED_PRUNED_COUNT = 2
FINGERPRINT_PROFILE = "fast"
FINGERPRINT_DIGEST = "abc123"


def test_runtime_events_record_run_artifacts(
    tmp_path: Path,
) -> None:
    """Profile adapter emits run-state and artifact event records."""

    sink = InMemoryRuntimeEventSink()
    events = runtime_eventing.ProfileRuntimeEvents(
        sink=sink,
        profile="fast",
        run_id="run-1",
    )
    artifact_events = runtime_eventing.artifact_events_for(events)

    runtime_eventing.run_fresh(
        events,
        log_dir=tmp_path / "runs" / "run-1",
        fingerprint=fingerprint_payload(),
    )
    runtime_eventing.run_reused(
        events,
        exit_code=0,
        log_dir=tmp_path,
        fingerprint=fingerprint_payload(),
    )
    runtime_eventing.manual_escalation(events, fingerprint=fingerprint_payload())
    artifact_events.artifact_written(path=".verify-logs/manifest.json", kind="manifest")
    artifact_events.artifact_removed(path=".verify-logs/LAST_FAILURE.md", kind="failure")
    artifact_events.artifact_retention_pruned(
        log_dir=tmp_path,
        pruned_count=EXPECTED_PRUNED_COUNT,
        keep=10,
    )

    assert [record["event_name"] for record in sink.records] == [
        "verifier.fresh",
        "verifier.reused",
        "manual.escalation",
        "artifact.written",
        "artifact.removed",
        "artifact.retention_pruned",
    ]
    assert sink.records[1]["status"] == "reused"
    assert event_attributes(sink.records[0])["fingerprint"] == fingerprint_payload()
    assert event_attributes(sink.records[2])["fingerprint"] == fingerprint_payload()
    assert event_attributes(sink.records[-1])["pruned_count"] == EXPECTED_PRUNED_COUNT


def event_attributes(record: dict[str, object]) -> dict[str, object]:
    """Return typed event attributes."""

    return cast("dict[str, object]", record["attributes"])


def fingerprint_payload() -> dict[str, object]:
    """Return verifier fingerprint fixture."""

    return {"profile": FINGERPRINT_PROFILE, "digest": FINGERPRINT_DIGEST}
