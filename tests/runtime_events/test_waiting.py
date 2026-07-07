"""Tests wait runtime event adapter."""

from __future__ import annotations

from typing import cast

import pytest

from agent_maintainer.runtime_events.sinks import InMemoryRuntimeEventSink
from agent_maintainer.runtime_events.waiting import (
    WaitRuntimeEvents,
    emit_cleaned,
    emit_heartbeat_noop,
    emit_terminal_claimed,
)

POLL_ATTEMPT = 2
CHECK_COUNT = 5


def test_wait_runtime_events_emit_poll_record() -> None:
    """Wait event adapter emits compact poll records."""

    sink = InMemoryRuntimeEventSink()
    events = WaitRuntimeEvents(sink=sink, target_kind="github-pr", target_id="303")

    events.polled(
        attempt=POLL_ATTEMPT,
        completed=True,
        status="completed",
        attributes={"check_count": CHECK_COUNT},
    )

    record = sink.records[0]
    assert record["event_name"] == "wait.poll"
    assert record["command"] == "wait"
    assert record["status"] == "completed"
    attributes = cast("dict[str, object]", record["attributes"])
    assert attributes["attempt"] == POLL_ATTEMPT
    assert attributes["check_count"] == CHECK_COUNT


def test_wait_runtime_events_emit_lifecycle_records() -> None:
    """Wait event adapter emits registration, sweep, ready, and resume records."""

    sink = InMemoryRuntimeEventSink()
    events = WaitRuntimeEvents(sink=sink, target_kind="github-run", target_id="123")

    events.registered(wait_id="wait-1", background=True)
    events.foreground_blocked(wait_id="wait-1")
    events.swept(checked=1, updated=1, pending=0, ready=1)
    events.ready(wait_id="wait-1", result="PASS")
    events.resumed(wait_id="wait-1")
    emit_heartbeat_noop(events)
    emit_terminal_claimed(events, wait_id="wait-1", result="PASS")
    emit_cleaned(events, expired_ready=1)

    assert [record["event_name"] for record in sink.records] == [
        "wait.registered",
        "wait.foreground_blocked",
        "wait.swept",
        "wait.ready",
        "wait.resumed",
        "wait.heartbeat_noop",
        "wait.terminal_claimed",
        "wait.cleaned",
    ]
    assert sink.records[0]["status"] == "background"
    assert sink.records[3]["status"] == "PASS"
    assert sink.records[5]["status"] == "pending"
    assert sink.records[6]["status"] == "PASS"
    assert sink.records[7]["status"] == "completed"


def test_wait_events_fallback_to_null_sink(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid runtime event config falls back to a null sink."""

    monkeypatch.setattr(
        "agent_maintainer.runtime_events.waiting.load_config",
        raise_bad_config,
    )

    events = WaitRuntimeEvents.create(target_kind="verifier", target_id="run-1")

    events.polled(attempt=1, completed=False, status="pending")


def raise_bad_config() -> None:
    """Raise deterministic config error."""

    raise ValueError("bad config")
