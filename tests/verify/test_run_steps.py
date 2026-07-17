"""Tests verifier run-step event instrumentation."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import cast

import pytest

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.core import artifact_environment
from agent_maintainer.models import Check, CheckResult
from agent_maintainer.runtime_events.sinks import InMemoryRuntimeEventSink
from agent_maintainer.verify import run_steps
from agent_maintainer.verify.runtime_eventing import ProfileRuntimeEvents
from tests.support.callbacks import constant_callback

MAX_LINES = 20
MAX_CHARS = 2000
FAIL_EXIT_CODE = 2


def test_collect_results_events(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Collected checks emit selection, start, finish, and failure events."""
    check = Check("sample-check", ["sample"], frozenset(("precommit",)))
    args = _args()
    sink = InMemoryRuntimeEventSink()
    events = ProfileRuntimeEvents(sink=sink, profile="precommit", run_id="run-1")

    _stub_validation(monkeypatch)
    monkeypatch.setattr(run_steps, "run_check", FailingCheckRunner(tmp_path))

    results = run_steps.collect_results(
        args,
        _config(tmp_path),
        [check],
        tmp_path,
        runtime_events=events,
    )

    assert [result.name for result in results] == ["sample-check"]
    assert [record["event_name"] for record in sink.records] == [
        "checks.selected",
        "check.started",
        "check.finished",
        "check.failed",
    ]
    assert {record["run_id"] for record in sink.records} == {"run-1"}
    assert sink.records[2]["status"] == "fail"
    assert sink.records[2]["exit_code"] == FAIL_EXIT_CODE


def test_collect_results_scopes_verification_profile_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Commands receive the active profile and the caller environment is restored."""
    observed: list[str | None] = []
    delegate = FailingCheckRunner(tmp_path)

    def observe_profile(
        check: Check,
        log_dir: Path,
        max_lines: int,
        max_chars: int,
    ) -> CheckResult:
        observed.append(os.environ.get(artifact_environment.VERIFY_PROFILE_ENV))
        return delegate(check, log_dir, max_lines, max_chars)

    _stub_validation(monkeypatch)
    monkeypatch.setenv(artifact_environment.VERIFY_PROFILE_ENV, "caller-value")
    monkeypatch.setattr(run_steps, "run_check", observe_profile)

    run_steps.collect_results(
        _args(),
        _config(tmp_path),
        [Check("sample-check", ["sample"], frozenset(("precommit",)))],
        tmp_path,
    )

    assert observed == ["precommit"]
    assert os.environ[artifact_environment.VERIFY_PROFILE_ENV] == "caller-value"


def test_collect_results_exception(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Unexpected check runner exceptions emit compact event before reraising."""
    check = Check("sample-check", ["sample"], frozenset(("precommit",)))
    sink = InMemoryRuntimeEventSink()
    events = ProfileRuntimeEvents(sink=sink, profile="precommit", run_id="run-2")

    _stub_validation(monkeypatch)
    monkeypatch.setattr(run_steps, "run_check", _raising_check)

    with pytest.raises(RuntimeError):
        run_steps.collect_results(
            _args(),
            _config(tmp_path),
            [check],
            tmp_path,
            runtime_events=events,
        )

    exception_attributes = cast("dict[str, object]", sink.records[2]["attributes"])
    assert [record["event_name"] for record in sink.records] == [
        "checks.selected",
        "check.started",
        "check.exception",
    ]
    assert exception_attributes["exception_type"] == "RuntimeError"
    assert "hunter2" not in str(exception_attributes["message"])


def _args() -> argparse.Namespace:
    """Return verifier args needed by collect_results."""
    return argparse.Namespace(
        profile="precommit",
        base_ref="HEAD",
        compare_branch="HEAD",
        max_lines=MAX_LINES,
        max_chars=MAX_CHARS,
    )


def _config(tmp_path: Path) -> MaintainerConfig:
    """Return minimal maintainer config for run-step tests."""
    return MaintainerConfig(
        diagnostic_artifacts_dir=str(tmp_path),
        source_roots=("src",),
        test_roots=("tests",),
    )


def _stub_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable unrelated layout and Git ref validation."""
    monkeypatch.setattr(run_steps, "layout_failures", constant_callback([]))
    monkeypatch.setattr(run_steps, "ref_failures", constant_callback(()))


class FailingCheckRunner:
    """Fake failing check runner."""

    def __init__(self, tmp_path: Path) -> None:
        """Store log directory for fake result."""
        self._tmp_path = tmp_path

    def __call__(
        self,
        _check: Check,
        _log_dir: Path,
        _max_lines: int,
        _max_chars: int,
    ) -> CheckResult:
        """Return fake failing check result."""
        return CheckResult(
            "sample-check",
            passed=False,
            exit_code=FAIL_EXIT_CODE,
            log_path=str(self._tmp_path / "sample-check.log"),
        )


def _raising_check(
    _check: Check,
    _log_dir: Path,
    _max_lines: int,
    _max_chars: int,
) -> CheckResult:
    """Raise a fake check runner exception."""
    raise RuntimeError("boom with password=hunter2")
