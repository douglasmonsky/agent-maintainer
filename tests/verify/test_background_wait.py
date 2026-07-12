"""Tests verifier background wait registration."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from agent_maintainer.verify import background_wait
from agent_maintainer.wait import broker as wait_broker
from agent_maintainer.wait import daemon_launchd
from agent_waits.watcher_state import watcher_state


def _unsupported_launchd(root: Path, _wait_id: str) -> daemon_launchd.DaemonLaunch:
    return daemon_launchd.DaemonLaunch(
        started=False,
        label="com.agent-maintainer.wait.test",
        log_path=root / "daemon.log",
        error="unsupported",
    )


def test_register_background_verifier_wait_uses_durable_watcher_policy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Direct verifier registration persists canonical strict-Codex failure."""

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(wait_broker, "ensure_wait_daemon", _unsupported_launchd)

    def reject_legacy_popen(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("verifier adapter must not launch its own watcher")

    monkeypatch.setattr(subprocess, "Popen", reject_legacy_popen)

    registration = background_wait.register_background_verifier_wait(
        "run-123",
        Path(".verify-logs"),
    )

    persisted = wait_broker.WaitRegistry(tmp_path).read(registration.record.wait_id)
    state = watcher_state(persisted)
    assert registration.watcher_started is False
    assert registration.watcher_strategy == ""
    assert "launchd required for Codex rewake" in registration.watcher_error
    assert persisted.kind == wait_broker.WAIT_KIND_VERIFIER
    assert persisted.target_id == "run-123"
    assert persisted.metadata is not None
    assert persisted.metadata["log_dir"] == ".verify-logs"
    assert state.strategy == "failed"
    assert state.error_code == "launchd_required"
