"""Tests background wait sweeper behavior."""

from __future__ import annotations

import subprocess
import time
from datetime import datetime
from pathlib import Path

import pytest

from agent_maintainer.verify import async_state
from agent_maintainer.wait.github_pr import (
    GitHubPrCheck,
    GitHubPrChecksState,
    GitHubPrWaitConfig,
)
from agent_maintainer.wait.registry import (
    RESULT_CANCELLED,
    RESULT_TIMEOUT,
    WAIT_STATUS_PENDING,
    WAIT_STATUS_READY,
    RegisterGitHubPrWait,
    RegisterVerifierWait,
    WaitRecord,
    WaitRegistry,
)
from agent_maintainer.wait.sweeper import (
    cleanup_waits,
    start_wait_watcher,
    sweep_once,
    sweep_ready_notifications,
    sweep_record,
    watch_wait,
)
from agent_maintainer.wait.sweeper_rendering import render_sweep_json, render_sweep_text

NOW = datetime.fromisoformat("2026-07-06T22:00:00+00:00")
LATER = datetime.fromisoformat("2026-07-06T22:01:00+00:00")
EXPIRED = datetime.fromisoformat("2026-07-06T23:01:00+00:00")
SWEEP_INTERVAL_SECONDS = 1
SWEEP_TIMEOUT_SECONDS = 3600
CANCELLED_PROCESS_STATUS = 143
FAKE_PROCESS_ID = 123


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


def test_sweep_persists_cancelled_verifier_terminal_state(tmp_path: Path) -> None:
    """Cancelled children complete their wait record without timing out."""

    log_dir = tmp_path / ".verify-logs"
    registry = WaitRegistry(tmp_path)
    record = registry.register_verifier(
        RegisterVerifierWait(root=tmp_path, run_id="cancelled", log_dir=log_dir, now=NOW),
    )
    write_cancelled_job(log_dir)

    completed = sweep_record(registry, record, now=LATER)

    assert completed.status == WAIT_STATUS_READY
    assert completed.terminal_result == RESULT_CANCELLED
    assert "Result: CANCELLED" in completed.resume_message
    assert completed.last_observed_state is not None
    assert completed.last_observed_state["cancelled"] is True


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
    assert watcher.pid == FAKE_PROCESS_ID
    assert popen_spy.calls[0]["cwd"] == tmp_path
    assert popen_spy.calls[0]["stdin"] == subprocess.DEVNULL
    assert popen_spy.calls[0]["stdout"] == subprocess.DEVNULL
    assert popen_spy.calls[0]["stderr"] == subprocess.DEVNULL
    assert popen_spy.calls[0]["close_fds"] is True
    assert popen_spy.calls[0]["start_new_session"] is True


def test_render_sweep_outputs_are_compact(tmp_path: Path) -> None:
    """Sweep renderers expose compact text and JSON summaries."""

    registry = WaitRegistry(tmp_path)
    register_wait(registry, tmp_path)

    summary = sweep_once(registry, query_checks=successful_query, now=LATER)

    assert "Result: PASS" in render_sweep_text(summary)
    assert '"updated": 1' in render_sweep_json(summary)


def test_cleanup_waits_expires_stale_ready(tmp_path: Path) -> None:
    """Cleanup expires ready records past the notification TTL."""

    registry = WaitRegistry(tmp_path)
    record = register_wait(registry, tmp_path)
    sweep_once(registry, query_checks=successful_query, now=LATER)

    summary = cleanup_waits(
        registry,
        ready_older_than_seconds=60,
        now=LATER.replace(minute=3),
    )

    assert summary.expired_ready == 1
    assert registry.read(record.wait_id).status != WAIT_STATUS_READY


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


def write_cancelled_job(log_dir: Path) -> None:
    """Write one signal-cancelled verifier job state."""

    now = time.time()
    jobs_dir = log_dir / "jobs"
    async_state.write_async_state(
        jobs_dir / "cancelled.json",
        async_state.AsyncVerifierState(
            run_id="cancelled",
            profile="full",
            status=async_state.JOB_STATUS_CANCELLED,
            process_id=FAKE_PROCESS_ID,
            command=("python", "-m", "agent_maintainer.verify.async_child"),
            fingerprint={},
            stdout_path=str(jobs_dir / "cancelled.stdout.log"),
            stderr_path=str(jobs_dir / "cancelled.stderr.log"),
            started_at=now,
            updated_at=now,
            exit_code=CANCELLED_PROCESS_STATUS,
            error="received signal SIGTERM",
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
        return type("Process", (), {"pid": FAKE_PROCESS_ID})()
