"""Tests background wait sweeper behavior."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from agent_maintainer.wait.github_pr import (
    GitHubPrCheck,
    GitHubPrChecksState,
    GitHubPrWaitConfig,
)
from agent_maintainer.wait.registry import (
    RESULT_TIMEOUT,
    WAIT_STATUS_PENDING,
    WAIT_STATUS_READY,
    RegisterGitHubPrWait,
    WaitRecord,
    WaitRegistry,
)
from agent_maintainer.wait.sweeper import (
    start_wait_watcher,
    sweep_once,
    sweep_ready_notifications,
    watch_wait,
)
from agent_maintainer.wait.sweeper_rendering import render_sweep_json, render_sweep_text

NOW = datetime.fromisoformat("2026-07-06T22:00:00+00:00")
LATER = datetime.fromisoformat("2026-07-06T22:01:00+00:00")
EXPIRED = datetime.fromisoformat("2026-07-06T23:01:00+00:00")
SWEEP_INTERVAL_SECONDS = 1
SWEEP_TIMEOUT_SECONDS = 3600


def test_sweep_once_completes_terminal_pr_wait(tmp_path: Path) -> None:
    """One-shot sweep records ready waits without foreground chatter."""

    registry = WaitRegistry(tmp_path)
    record = register_wait(registry, tmp_path)

    summary = sweep_once(registry, query_checks=successful_query, now=LATER)
    completed = registry.read(record.wait_id)

    assert summary.checked == 1
    assert summary.updated == 1
    assert completed.status == WAIT_STATUS_READY
    assert completed.terminal_result == "PASS"
    assert "Result: PASS" in completed.resume_message


def test_sweep_observes_pending_quietly(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """One-shot sweep updates pending state without printing chatter."""

    registry = WaitRegistry(tmp_path)
    record = register_wait(registry, tmp_path)

    summary = sweep_once(registry, query_checks=pending_query, now=LATER)
    pending = registry.read(record.wait_id)

    assert summary.pending == 1
    assert pending.status == WAIT_STATUS_PENDING
    assert pending.last_observed_state is not None
    assert capsys.readouterr().out == ""


def test_sweep_once_times_out_expired_wait(tmp_path: Path) -> None:
    """One-shot sweep marks expired waits ready for resume."""

    registry = WaitRegistry(tmp_path)
    record = register_wait(registry, tmp_path)

    def fail_query(_config: GitHubPrWaitConfig) -> GitHubPrChecksState:
        raise AssertionError("expired waits should not poll")

    summary = sweep_once(registry, query_checks=fail_query, now=EXPIRED)
    completed = registry.read(record.wait_id)

    assert summary.ready == 1
    assert completed.terminal_result == RESULT_TIMEOUT
    assert completed.status == WAIT_STATUS_READY


def test_repo_heartbeat_claims_new_ready_wait_once(tmp_path: Path) -> None:
    """Repo heartbeat sweeps and emits each ready wait once."""

    registry = WaitRegistry(tmp_path)
    record = register_wait(registry, tmp_path)

    claimed = sweep_ready_notifications(
        registry,
        query_checks=successful_query,
        now=LATER,
    )
    second_claim = sweep_ready_notifications(
        registry,
        query_checks=successful_query,
        now=LATER.replace(minute=2),
    )

    assert [item.wait_id for item in claimed] == [record.wait_id]
    assert second_claim == ()


def test_watch_wait_returns_after_terminal_poll(tmp_path: Path) -> None:
    """Watch mode sleeps while pending and returns terminal record."""

    registry = WaitRegistry(tmp_path)
    record = register_wait(registry, tmp_path)
    queries = QuerySequence((pending_state("291"), success_state("291")))
    sleeps: list[int] = []

    completed = watch_wait(
        registry,
        record.wait_id,
        query_checks=queries,
        sleep=sleeps.append,
        now=LATER,
    )

    assert completed.status == WAIT_STATUS_READY
    assert completed.terminal_result == "PASS"
    assert sleeps == [record.interval_seconds]


def test_start_wait_watcher_uses_quiet_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Detached watcher command targets one wait and silences output."""

    popen_spy = PopenSpy()
    monkeypatch.setattr("agent_maintainer.wait.sweeper.subprocess.Popen", popen_spy)

    watcher = start_wait_watcher(tmp_path, "wait-1", python_executable="python")

    assert watcher.command[:4] == ("python", "-m", "agent_maintainer", "wait")
    assert "--watch" in watcher.command
    assert popen_spy.calls[0]["cwd"] == tmp_path
    assert popen_spy.calls[0]["start_new_session"] is True


def test_render_sweep_outputs_are_compact(tmp_path: Path) -> None:
    """Sweep renderers expose compact text and JSON summaries."""

    registry = WaitRegistry(tmp_path)
    register_wait(registry, tmp_path)

    summary = sweep_once(registry, query_checks=successful_query, now=LATER)

    assert "Result: PASS" in render_sweep_text(summary)
    assert '"updated": 1' in render_sweep_json(summary)


def register_wait(registry: WaitRegistry, root: Path) -> WaitRecord:
    """Register one deterministic wait for sweeper tests."""

    return registry.register_github_pr(
        RegisterGitHubPrWait(
            root=root,
            pr_number="291",
            repo="douglasmonsky/agent-maintainer",
            interval_seconds=SWEEP_INTERVAL_SECONDS,
            timeout_seconds=SWEEP_TIMEOUT_SECONDS,
            now=NOW,
        ),
    )


def successful_query(config: GitHubPrWaitConfig) -> GitHubPrChecksState:
    """Return a successful PR check state."""

    return success_state(config.pr_number)


def pending_query(config: GitHubPrWaitConfig) -> GitHubPrChecksState:
    """Return a pending PR check state."""

    return pending_state(config.pr_number)


def success_state(pr_number: str) -> GitHubPrChecksState:
    """Return successful PR checks."""

    return GitHubPrChecksState(
        pr_number=pr_number,
        checks=(GitHubPrCheck(name="verify", state="success"),),
    )


def pending_state(pr_number: str) -> GitHubPrChecksState:
    """Return pending PR checks."""

    return GitHubPrChecksState(
        pr_number=pr_number,
        checks=(GitHubPrCheck(name="verify", state="in_progress"),),
    )


class QuerySequence:
    """Query callable returning states in order."""

    def __init__(self, states: tuple[GitHubPrChecksState, ...]) -> None:
        self._states = list(states)

    def __call__(self, _config: GitHubPrWaitConfig) -> GitHubPrChecksState:
        return self._states.pop(0)


class PopenSpy:
    """Callable recording detached watcher process launches."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def __call__(self, command: list[str], **kwargs: object) -> object:
        self.calls.append({"command": command, **kwargs})
        return object()
