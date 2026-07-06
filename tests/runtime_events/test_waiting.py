"""Tests wait runtime event adapter."""

from __future__ import annotations

from typing import cast

import pytest

from agent_maintainer.runtime_events.sinks import InMemoryRuntimeEventSink
from agent_maintainer.runtime_events.waiting import WaitRuntimeEvents

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
