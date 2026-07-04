"""Tests verifier runtime event adapter."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from agent_maintainer.models import Check, CheckResult
from agent_maintainer.runtime_events.sinks import InMemoryRuntimeEventSink
from agent_maintainer.verify.runtime_eventing import ProfileRuntimeEvents


def test_profile_lifecycle_events(tmp_path: Path) -> None:
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


def test_check_boundary_events() -> None:
    """Profile runtime adapter emits compact check boundary events."""
    sink = InMemoryRuntimeEventSink()
    events = ProfileRuntimeEvents(sink=sink, profile="precommit", run_id="run-2")
    check = Check("ruff-check", ["ruff", "check"], frozenset(("precommit",)))
    result = CheckResult(
        "ruff-check",
        passed=False,
        exit_code=1,
        log_path=".verify-logs/runs/run-2/ruff-check.log",
        artifact_paths=("ruff.json",),
    )

    events.selected([check])
    events.check_started(check)
    events.check_finished(result)

    _assert_check_sequence(sink.records)
    _assert_failed_check_record(sink.records[2])


def test_skip_and_exception_events() -> None:
    """Profile runtime adapter emits skip and sanitized exception boundaries."""
    sink = InMemoryRuntimeEventSink()
    events = ProfileRuntimeEvents(sink=sink, profile="security", run_id="run-3")
    check = Check("pip-audit", ["pip-audit"], frozenset(("security",)))
    result = CheckResult(
        "pip-audit",
        passed=True,
        skipped=True,
        skip_status="missing_optional",
        log_path=".verify-logs/runs/run-3/pip-audit.log",
    )

    events.check_finished(result)
    events.check_exception(check, RuntimeError("failed with token=secret-value"))

    exception_attributes = cast("dict[str, object]", sink.records[2]["attributes"])
    assert [record["event_name"] for record in sink.records] == [
        "check.finished",
        "check.skipped",
        "check.exception",
    ]
    assert sink.records[0]["status"] == "missing_optional"
    assert exception_attributes["exception_type"] == "RuntimeError"
    assert "secret-value" not in str(exception_attributes["message"])


def _assert_check_sequence(records: list[dict[str, object]]) -> None:
    """Assert check lifecycle event names and selection attributes."""
    selected_attributes = cast("dict[str, object]", records[0]["attributes"])
    assert [record["event_name"] for record in records] == [
        "checks.selected",
        "check.started",
        "check.finished",
        "check.failed",
    ]
    assert selected_attributes["count"] == 1
    assert selected_attributes["checks"] == ["ruff-check"]


def _assert_failed_check_record(record: dict[str, object]) -> None:
    """Assert failed check event fields."""
    attributes = cast("dict[str, object]", record["attributes"])
    assert record["status"] == "fail"
    assert record["exit_code"] == 1
    assert attributes["artifact_paths"] == ["ruff.json"]
