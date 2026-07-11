"""Tests daemon watcher selection in wait broker."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer.wait import broker, daemon_launchd
from agent_maintainer.wait.registry import RegisterGitHubPrWait, WaitRegistry
from agent_maintainer.wait.sweeper import DetachedWatcher
from agent_waits.watcher_state import watcher_state

PR_NUMBER = "291"
WATCHER_PID = 123


def _failed_daemon(root: Path, _wait_id: str) -> daemon_launchd.DaemonLaunch:
    return daemon_launchd.DaemonLaunch(
        started=False,
        label="com.agent-maintainer.wait.test",
        log_path=root / "daemon.log",
        error="launchd failed",
    )


def _started_watcher(_root: Path, _wait_id: str) -> DetachedWatcher:
    return DetachedWatcher(command=("python",), pid=WATCHER_PID)


def test_start_registered_watcher_reports_launchd_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Broker reports launchd failure when popen fallback starts."""

    registry = WaitRegistry(tmp_path)
    record = registry.register_github_pr(
        RegisterGitHubPrWait(root=tmp_path, pr_number=PR_NUMBER, platform="claude"),
    )
    monkeypatch.setattr(
        broker,
        "ensure_wait_daemon",
        _failed_daemon,
    )
    monkeypatch.setattr(
        broker,
        "start_wait_watcher",
        _started_watcher,
    )

    registration = broker.start_registered_watcher(tmp_path, record)

    assert registration.watcher_started
    assert registration.watcher_strategy == "popen"
    assert registration.watcher_error == "launchd fallback: launchd failed"
    persisted = watcher_state(registry.read(record.wait_id))
    assert persisted.strategy == "popen"
    assert persisted.pid == WATCHER_PID


def test_codex_rewake_requires_launchd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Codex rewake does not silently downgrade to popen."""

    registry = WaitRegistry(tmp_path)
    record = registry.register_github_pr(
        RegisterGitHubPrWait(root=tmp_path, pr_number=PR_NUMBER, platform="codex"),
    )
    monkeypatch.setattr(
        broker,
        "ensure_wait_daemon",
        _failed_daemon,
    )

    registration = broker.start_registered_watcher(tmp_path, record)

    assert not registration.watcher_started
    assert registration.watcher_strategy == ""
    assert registration.watcher_error == "launchd required for Codex rewake: launchd failed"


def test_start_registered_watcher_reports_both_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Broker reports both launchd and popen failures."""

    registry = WaitRegistry(tmp_path)
    record = registry.register_github_pr(
        RegisterGitHubPrWait(root=tmp_path, pr_number=PR_NUMBER, platform="claude"),
    )
    monkeypatch.setattr(
        broker,
        "ensure_wait_daemon",
        _failed_daemon,
    )

    def fail_watcher(root: Path, wait_id: str) -> None:
        raise OSError("popen failed")

    monkeypatch.setattr(broker, "start_wait_watcher", fail_watcher)

    registration = broker.start_registered_watcher(tmp_path, record)

    assert not registration.watcher_started
    assert registration.watcher_error == "launchd: launchd failed; popen: popen failed"
