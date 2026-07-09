"""Tests repo-scoped wait daemon helpers."""

from __future__ import annotations

import plistlib
import stat
import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest

from agent_maintainer.wait import daemon, daemon_launchd, daemon_plist, daemon_state
from agent_maintainer.wait.codex_rewake import (
    CODEX_BIN_ENV,
    CODEX_REWAKE_ENV,
    CODEX_THREAD_ID_ENV,
    CODEX_THREAD_ID_OVERRIDE_ENV,
)
from agent_maintainer.wait.github_pr import (
    GitHubPrCheck,
    GitHubPrChecksState,
    GitHubPrWaitResult,
)
from agent_maintainer.wait.registry import (
    WAIT_STATUS_RESUMED,
    RegisterGitHubPrWait,
    WaitRecord,
    WaitRegistry,
)

ENVELOPE_MODE = 0o600
PID = 123
THREAD_ID = "thread-123"


def test_launchd_label_stable_and_plist_safe(tmp_path: Path) -> None:
    """LaunchAgent plist is stable and excludes transient rewake metadata."""

    root = tmp_path / "repo"
    root.mkdir()
    label = daemon_launchd.launchd_label(root)
    plist_path = tmp_path / "wait.plist"
    daemon_plist.write_launch_agent_plist(
        daemon_plist.LaunchAgentPlist(
            path=plist_path,
            root=root,
            label=label,
            log_path=root / ".verify-logs" / "watchers" / "daemon.log",
            python_executable="/usr/bin/python3",
            interval_seconds=daemon_launchd.DAEMON_INTERVAL_SECONDS,
            idle_timeout_seconds=daemon_launchd.DAEMON_IDLE_TIMEOUT_SECONDS,
        ),
    )

    assert label == daemon_launchd.launchd_label(root)
    assert label.startswith("com.agent-maintainer.wait.")

    raw = plist_path.read_text(encoding="utf-8")
    assert THREAD_ID not in raw
    assert CODEX_THREAD_ID_ENV not in raw
    assert "OPENAI_API_KEY" not in raw
    assert "continuation prompt" not in raw

    payload = plistlib.loads(plist_path.read_bytes())
    assert payload["ProgramArguments"][:5] == [
        "/usr/bin/python3",
        "-m",
        "agent_maintainer",
        "wait",
        "daemon",
    ]
    assert payload["ProgramArguments"][5] == "run"
    assert payload["EnvironmentVariables"] == {
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(root / "src"),
    }


def test_rewake_envelope_is_private_minimal_and_read_once(tmp_path: Path) -> None:
    """Rewake envelope stores only transient env and is deleted after read."""

    wait_id = "github-pr-291"
    path = daemon_state.write_rewake_envelope(
        tmp_path,
        wait_id,
        {
            CODEX_THREAD_ID_ENV: THREAD_ID,
            CODEX_REWAKE_ENV: "1",
            CODEX_BIN_ENV: "/usr/local/bin/codex",
            "PROMPT": "do not persist",
        },
    )

    mode = stat.S_IMODE(path.stat().st_mode)
    assert mode == ENVELOPE_MODE
    raw = path.read_text(encoding="utf-8")
    assert THREAD_ID in raw
    assert "PROMPT" not in raw

    env = daemon_state.read_rewake_envelope(tmp_path, wait_id)
    assert env == {
        CODEX_THREAD_ID_OVERRIDE_ENV: THREAD_ID,
        CODEX_REWAKE_ENV: "1",
        CODEX_BIN_ENV: "/usr/local/bin/codex",
    }
    assert not path.exists()
    assert daemon_state.read_rewake_envelope(tmp_path, wait_id) is None


def test_invalid_rewake_envelope_is_deleted(tmp_path: Path) -> None:
    """Invalid envelopes do not crash daemon sweeps."""

    path = daemon_state.rewake_envelope_path(tmp_path, "wait-1")
    path.parent.mkdir(parents=True)
    path.write_text("{", encoding="utf-8")

    assert daemon_state.read_rewake_envelope(tmp_path, "wait-1") is None
    assert not path.exists()


def test_rewake_envelope_rejects_missing_thread(tmp_path: Path) -> None:
    """Rewake envelopes require transient thread metadata."""

    with pytest.raises(RuntimeError, match="thread id"):
        daemon_state.write_rewake_envelope(
            tmp_path,
            "wait-1",
            {CODEX_REWAKE_ENV: "1"},
        )


def test_rewake_envelope_without_env_is_deleted(tmp_path: Path) -> None:
    """Malformed envelope payloads are ignored and removed."""

    path = daemon_state.rewake_envelope_path(tmp_path, "wait-1")
    path.parent.mkdir(parents=True)
    path.write_text('{"expires_at": "2999-01-01T00:00:00Z"}', encoding="utf-8")

    assert daemon_state.read_rewake_envelope(tmp_path, "wait-1") is None
    assert not path.exists()


def test_has_rewake_envelope_handles_valid_expired_and_missing(tmp_path: Path) -> None:
    """Envelope presence check removes expired state."""

    valid = daemon_state.write_rewake_envelope(
        tmp_path,
        "valid",
        {CODEX_THREAD_ID_ENV: THREAD_ID, CODEX_REWAKE_ENV: "1"},
    )
    expired = daemon_state.rewake_envelope_path(tmp_path, "expired")
    expired.parent.mkdir(parents=True)
    expired.write_text('{"expires_at": "2000-01-01T00:00:00Z", "env": {}}', encoding="utf-8")

    assert daemon_state.has_rewake_envelope(tmp_path, "valid")
    assert not daemon_state.has_rewake_envelope(tmp_path, "expired")
    assert not expired.exists()
    assert not daemon_state.has_rewake_envelope(tmp_path, "missing")
    valid.unlink()


def test_read_heartbeat_handles_missing_and_invalid(tmp_path: Path) -> None:
    """Heartbeat reader treats missing and invalid JSON as empty."""

    assert daemon_state.read_heartbeat(tmp_path) == ""
    path = daemon_state.watchers_dir(tmp_path) / daemon_state.DAEMON_HEARTBEAT_NAME
    path.parent.mkdir(parents=True)
    path.write_text("{", encoding="utf-8")

    assert daemon_state.read_heartbeat(tmp_path) == ""


def test_install_launch_agent_uses_fake_launchctl_and_temp_home(tmp_path: Path) -> None:
    """LaunchAgent install writes plist and calls bootstrap/kickstart."""

    calls: list[Sequence[str]] = []

    def runner(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    result = daemon_launchd.install_launch_agent(
        tmp_path,
        options=daemon_launchd.LaunchAgentInstallOptions(
            runner=runner,
            python_executable="/usr/bin/python3",
            home=tmp_path / "home",
        ),
    )

    assert result.started
    assert result.label == daemon_launchd.launchd_label(tmp_path.resolve())
    assert daemon_launchd.launch_agent_path(result.label, home=tmp_path / "home").exists()
    assert any(command[1] == "bootstrap" for command in calls)
    assert any(command[1] == "kickstart" for command in calls)


def test_ensure_wait_daemon_unsupported(tmp_path: Path) -> None:
    """Daemon ensure reports unsupported when rewake prerequisites are absent."""

    result = daemon_launchd.ensure_wait_daemon(tmp_path, "wait-1", env={})

    assert not result.started
    assert result.error == "unsupported"


def test_ensure_wait_daemon_success_and_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Daemon ensure writes envelope and reports launchd failures compactly."""

    calls: list[Sequence[str]] = []

    def runner(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    env = {
        CODEX_REWAKE_ENV: "1",
        CODEX_THREAD_ID_ENV: THREAD_ID,
        CODEX_BIN_ENV: "/bin/echo",
    }
    monkeypatch.setattr(
        daemon_launchd,
        "launchd_rewake_supported",
        lambda current: True,
    )
    success = daemon_launchd.ensure_wait_daemon(
        tmp_path,
        "wait-ok",
        env=env,
        runner=runner,
        python_executable="/usr/bin/python3",
    )

    assert success.started
    assert calls

    def failing_runner(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="boom")

    failed = daemon_launchd.ensure_wait_daemon(
        tmp_path,
        "wait-fail",
        env=env,
        runner=failing_runner,
        python_executable="/usr/bin/python3",
    )

    assert not failed.started
    assert "boom" in failed.error


def test_daemon_status_parses_pid_and_heartbeat(tmp_path: Path) -> None:
    """Launchd status reports loaded pid and heartbeat."""

    daemon_state.write_heartbeat(tmp_path, summary_checked=1, resumed=0)

    def runner(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, stdout="pid = 123\n", stderr="")

    status = daemon_launchd.daemon_status(tmp_path, runner=runner, home=tmp_path / "home")
    text = daemon_launchd.status_text(status)

    assert status.loaded
    assert status.pid == PID
    assert status.last_heartbeat
    assert "PID: 123" in text
    assert "Last heartbeat:" in text


def test_daemon_status_reports_launchctl_error(tmp_path: Path) -> None:
    """Launchd status reports compact launchctl error."""

    def runner(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="missing")

    status = daemon_launchd.daemon_status(tmp_path, runner=runner, home=tmp_path / "home")

    assert not status.loaded
    assert status.error == "missing"


def test_daemon_run_resumes_ready_wait_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Daemon consumes envelope and marks ready wait resumed."""

    registry = WaitRegistry(tmp_path)
    record = completed_pr_wait(registry, tmp_path)
    daemon_state.write_rewake_envelope(
        tmp_path,
        record.wait_id,
        {
            CODEX_THREAD_ID_ENV: THREAD_ID,
            CODEX_REWAKE_ENV: "1",
            CODEX_BIN_ENV: "/usr/local/bin/codex",
        },
    )
    calls: list[tuple[str, str]] = []

    class FakeBackend:
        def __init__(self, registry: WaitRegistry, *, env: dict[str, str]) -> None:
            self._registry = registry
            self._env = env

        def resume_if_available(self, record: WaitRecord) -> str:
            calls.append((record.wait_id, self._env[CODEX_THREAD_ID_OVERRIDE_ENV]))
            self._registry.mark_resumed(record)
            return "resumed"

    monkeypatch.setattr(daemon, "CodexRewakeBackend", FakeBackend)
    monkeypatch.setattr(daemon, "codex_rewake_resumed", lambda result: result == "resumed")

    now = {"value": 0.0}

    def sleep(seconds: float) -> None:
        now["value"] += seconds

    status = daemon.run_daemon(
        tmp_path,
        interval_seconds=2,
        idle_timeout_seconds=1,
        hooks=daemon.DaemonLoopHooks(
            sleep=sleep,
            monotonic=lambda: now["value"],
            env={},
        ),
    )

    assert status == 0
    assert calls == [(record.wait_id, THREAD_ID)]
    assert registry.read(record.wait_id).status == WAIT_STATUS_RESUMED
    assert not daemon_state.rewake_envelope_path(tmp_path, record.wait_id).exists()


def completed_pr_wait(registry: WaitRegistry, root: Path) -> WaitRecord:
    """Create ready PR wait record."""

    record = registry.register_github_pr(RegisterGitHubPrWait(root=root, pr_number="291"))
    return registry.complete_github_pr(
        record,
        GitHubPrWaitResult(
            pr_number="291",
            state=GitHubPrChecksState(
                pr_number="291",
                checks=(GitHubPrCheck(name="verify", state="success"),),
            ),
        ),
    )
