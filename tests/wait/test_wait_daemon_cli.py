"""Tests wait daemon CLI branches."""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest

from agent_maintainer.wait import cli, daemon_launchd

ERROR_EXIT_CODE = 2
PID = 123
RUN_IDLE_TIMEOUT_SECONDS = 11
RUN_INTERVAL_SECONDS = 7


def _daemon_status(root: Path) -> daemon_launchd.DaemonStatus:
    return daemon_launchd.DaemonStatus(
        label="com.agent-maintainer.wait.test",
        plist_path=root / "agent.plist",
        log_path=root / "daemon.log",
        loaded=True,
        pid=PID,
        last_heartbeat="2026-07-09T00:00:00Z",
    )


def _successful_install(
    root: Path,
    *,
    options: daemon_launchd.LaunchAgentInstallOptions,
) -> daemon_launchd.DaemonLaunch:
    del options
    return daemon_launchd.DaemonLaunch(
        started=True,
        label="com.agent-maintainer.wait.test",
        log_path=root / "daemon.log",
    )


def _failed_install(
    root: Path,
    *,
    options: daemon_launchd.LaunchAgentInstallOptions,
) -> daemon_launchd.DaemonLaunch:
    del options
    return daemon_launchd.DaemonLaunch(
        started=False,
        label="com.agent-maintainer.wait.test",
        log_path=root / "daemon.log",
        error="boom",
    )


def _unloaded_status(root: Path) -> daemon_launchd.DaemonStatus:
    return daemon_launchd.DaemonStatus(
        label="com.agent-maintainer.wait.test",
        plist_path=root / "agent.plist",
        log_path=root / "daemon.log",
        loaded=False,
        error="not loaded",
    )


def test_daemon_cli_status_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Daemon CLI renders status JSON."""

    monkeypatch.setattr(
        cli.daemon_launchd,
        "daemon_status",
        _daemon_status,
    )

    status = cli.main(["daemon", "status", "--root", str(tmp_path), "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert status == 0
    assert payload["loaded"] is True
    assert payload["pid"] == PID


def test_daemon_cli_install_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Daemon CLI install branch renders launch text."""

    monkeypatch.setattr(
        cli.daemon_launchd,
        "install_launch_agent",
        _successful_install,
    )

    status = cli.main(["daemon", "install", "--root", str(tmp_path)])
    output = capsys.readouterr().out

    assert status == 0
    assert "daemon installed: com.agent-maintainer.wait.test" in output
    assert str(tmp_path / "daemon.log") in output


def test_daemon_cli_install_json_and_failure_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Daemon CLI covers install JSON and failed text rendering."""

    monkeypatch.setattr(
        cli.daemon_launchd,
        "install_launch_agent",
        _successful_install,
    )
    status = cli.main(["daemon", "install", "--root", str(tmp_path), "--format", "json"])
    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["started"] is True

    monkeypatch.setattr(
        cli.daemon_launchd,
        "install_launch_agent",
        _failed_install,
    )
    status = cli.main(["daemon", "install", "--root", str(tmp_path)])
    assert status == 1
    assert "daemon not started: boom" in capsys.readouterr().out


def test_daemon_cli_unknown_command_returns_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Daemon command handler has defensive unknown-command branch."""

    def parse_unknown(_argv: list[str]) -> Namespace:
        return Namespace(command="daemon", daemon_command="other")

    monkeypatch.setattr(cli, "parse_args", parse_unknown)

    status = cli.main([])

    assert status == ERROR_EXIT_CODE


def test_daemon_cli_uninstall_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Daemon CLI uninstall branch renders status text."""

    monkeypatch.setattr(
        cli.daemon_launchd,
        "uninstall_launch_agent",
        _unloaded_status,
    )

    status = cli.main(["daemon", "uninstall", "--root", str(tmp_path)])
    output = capsys.readouterr().out

    assert status == 0
    assert "Result: not loaded" in output
    assert "Error: not loaded" in output


def test_daemon_cli_run_delegates_loop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Daemon CLI run branch delegates loop arguments."""

    calls: list[tuple[Path, int, int]] = []

    def run_daemon(root: Path, *, interval_seconds: int, idle_timeout_seconds: int) -> int:
        calls.append((root, interval_seconds, idle_timeout_seconds))
        return 0

    monkeypatch.setattr(cli.daemon, "run_daemon", run_daemon)

    status = cli.main(
        [
            "daemon",
            "run",
            "--root",
            str(tmp_path),
            "--interval",
            str(RUN_INTERVAL_SECONDS),
            "--idle-timeout",
            str(RUN_IDLE_TIMEOUT_SECONDS),
        ],
    )

    assert status == 0
    assert calls == [(tmp_path, RUN_INTERVAL_SECONDS, RUN_IDLE_TIMEOUT_SECONDS)]
