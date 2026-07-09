"""Tests Codex wait CLI background conversion behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer.wait import cli, daemon_launchd

PR_NUMBER = "291"


def test_codex_pr_cli_backgrounds_wait(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Codex foreground PR waits convert into background registrations."""

    calls: list[tuple[Path, str]] = []
    monkeypatch.delenv("AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT", raising=False)
    monkeypatch.setenv("CODEX_SHELL", "1")
    monkeypatch.setattr(
        "agent_maintainer.wait.broker.ensure_wait_daemon",
        lambda root, wait_id: (
            calls.append((root, wait_id))
            or daemon_launchd.DaemonLaunch(
                started=False,
                label="com.agent-maintainer.wait.test",
                log_path=tmp_path / "daemon.log",
                error="unsupported",
            )
        ),
    )

    status = cli.main(
        [
            "github-pr",
            PR_NUMBER,
            "--repo",
            "douglasmonsky/agent-maintainer",
            "--root",
            str(tmp_path),
            "--interval",
            "1",
            "--timeout-seconds",
            "2",
        ],
    )

    output = capsys.readouterr().out
    assert_success(status)
    assert "Result: PENDING" in output
    assert "manual resume:" in output
    assert "heartbeat request:" in output
    assert '"type": "codex_heartbeat_wait"' in output
    assert "watcher: not started (launchd required for Codex rewake: unsupported)" in output
    assert len(calls) == 1


def test_codex_rewake_pr_background_uses_launchd_daemon(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Codex rewake background waits prefer launchd daemon when available."""

    calls: list[tuple[Path, str]] = []
    monkeypatch.delenv("AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT", raising=False)
    monkeypatch.setenv("CODEX_SHELL", "1")
    monkeypatch.setattr(
        "agent_maintainer.wait.broker.ensure_wait_daemon",
        lambda root, wait_id: (
            calls.append((root, wait_id))
            or daemon_launchd.DaemonLaunch(
                started=True,
                label="com.agent-maintainer.wait.test",
                log_path=tmp_path / "daemon.log",
            )
        ),
    )

    status = cli.main(
        [
            "github-pr",
            PR_NUMBER,
            "--repo",
            "douglasmonsky/agent-maintainer",
            "--root",
            str(tmp_path),
            "--interval",
            "1",
            "--timeout-seconds",
            "2",
        ],
    )

    output = capsys.readouterr().out
    assert_success(status)
    assert "watcher: started via launchd" in output
    assert "com.agent-maintainer.wait.test" in output
    assert str(tmp_path / "daemon.log") in output
    assert len(calls) == 1


def test_codex_github_run_cli_backgrounds_wait(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Codex foreground GitHub run waits convert into background registrations."""

    calls: list[tuple[Path, str]] = []
    monkeypatch.delenv("AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT", raising=False)
    monkeypatch.setenv("CODEX_SHELL", "1")
    monkeypatch.setattr(
        "agent_maintainer.wait.broker.ensure_wait_daemon",
        lambda root, wait_id: (
            calls.append((root, wait_id))
            or daemon_launchd.DaemonLaunch(
                started=False,
                label="com.agent-maintainer.wait.test",
                log_path=tmp_path / "daemon.log",
                error="unsupported",
            )
        ),
    )

    status = cli.main(
        [
            "github-run",
            "123",
            "--repo",
            "douglasmonsky/agent-maintainer",
            "--root",
            str(tmp_path),
            "--interval",
            "1",
            "--timeout-seconds",
            "2",
        ],
    )

    output = capsys.readouterr().out
    assert_success(status)
    assert "Result: PENDING" in output
    assert "github-run wait registered" in output
    assert '"wait_kind": "github-run"' in output
    assert "watcher: not started (launchd required for Codex rewake: unsupported)" in output
    assert calls and calls[0][0] == tmp_path


def test_codex_verifier_cli_backgrounds_wait(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Codex foreground verifier waits convert into background registrations."""

    calls: list[tuple[Path, str]] = []
    monkeypatch.delenv("AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT", raising=False)
    monkeypatch.setenv("CODEX_SHELL", "1")
    monkeypatch.setattr(
        "agent_maintainer.wait.broker.ensure_wait_daemon",
        lambda root, wait_id: (
            calls.append((root, wait_id))
            or daemon_launchd.DaemonLaunch(
                started=False,
                label="com.agent-maintainer.wait.test",
                log_path=tmp_path / "daemon.log",
                error="unsupported",
            )
        ),
    )

    status = cli.main(
        [
            "verifier",
            "run-1",
            "--root",
            str(tmp_path),
            "--interval",
            "1",
            "--timeout-seconds",
            "2",
        ],
    )

    output = capsys.readouterr().out
    assert_success(status)
    assert "Result: PENDING" in output
    assert "verifier wait registered" in output
    assert '"wait_kind": "verifier"' in output
    assert "watcher: not started (launchd required for Codex rewake: unsupported)" in output
    assert calls and calls[0][0] == tmp_path


def assert_success(status: int) -> None:
    """Assert CLI command succeeded."""

    assert status == 0
