"""Tests daemon watcher selection in wait broker."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer.wait import broker, daemon_launchd
from agent_maintainer.wait.registry import RegisterGitHubPrWait, WaitRegistry

PR_NUMBER = "291"


def test_start_registered_watcher_reports_launchd_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Broker reports launchd failure when popen fallback starts."""

    registry = WaitRegistry(tmp_path)
    record = registry.register_github_pr(
        RegisterGitHubPrWait(root=tmp_path, pr_number=PR_NUMBER),
    )
    monkeypatch.setattr(
        broker,
        "ensure_wait_daemon",
        lambda root, wait_id: daemon_launchd.DaemonLaunch(
            started=False,
            label="com.agent-maintainer.wait.test",
            log_path=tmp_path / "daemon.log",
            error="launchd failed",
        ),
    )
    monkeypatch.setattr(broker, "start_wait_watcher", lambda root, wait_id: None)

    registration = broker.start_registered_watcher(tmp_path, record)

    assert registration.watcher_started
    assert registration.watcher_strategy == "popen"
    assert registration.watcher_error == "launchd fallback: launchd failed"


def test_start_registered_watcher_reports_both_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Broker reports both launchd and popen failures."""

    registry = WaitRegistry(tmp_path)
    record = registry.register_github_pr(
        RegisterGitHubPrWait(root=tmp_path, pr_number=PR_NUMBER),
    )
    monkeypatch.setattr(
        broker,
        "ensure_wait_daemon",
        lambda root, wait_id: daemon_launchd.DaemonLaunch(
            started=False,
            label="com.agent-maintainer.wait.test",
            log_path=tmp_path / "daemon.log",
            error="launchd failed",
        ),
    )

    def fail_watcher(root: Path, wait_id: str) -> None:
        raise OSError("popen failed")

    monkeypatch.setattr(broker, "start_wait_watcher", fail_watcher)

    registration = broker.start_registered_watcher(tmp_path, record)

    assert not registration.watcher_started
    assert registration.watcher_error == "launchd: launchd failed; popen: popen failed"
