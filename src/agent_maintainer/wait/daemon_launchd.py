"""LaunchAgent management for repo wait daemon."""

from __future__ import annotations

import hashlib
import os
import subprocess  # nosec B404
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from agent_maintainer.wait.codex_rewake import CODEX_REWAKE_ENV, codex_binary
from agent_maintainer.wait.daemon_plist import LaunchAgentPlist, write_launch_agent_plist
from agent_maintainer.wait.daemon_state import (
    daemon_log_path,
    read_heartbeat,
    write_rewake_envelope,
)

DAEMON_IDLE_TIMEOUT_SECONDS: Final = 1800
DAEMON_INTERVAL_SECONDS: Final = 5
LABEL_HASH_LENGTH: Final = 12
LAUNCHD_LABEL_PREFIX: Final = "com.agent-maintainer.wait"
LaunchctlRunner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class DaemonLaunch:
    """Result ensuring repo wait daemon."""

    started: bool
    label: str
    log_path: Path
    error: str = ""


@dataclass(frozen=True)
class DaemonStatus:
    """Current status of one repo wait daemon."""

    label: str
    plist_path: Path
    log_path: Path
    loaded: bool
    pid: int | None = None
    last_heartbeat: str = ""
    error: str = ""


@dataclass(frozen=True)
class LaunchAgentInstallOptions:
    """Optional dependencies for LaunchAgent installation."""

    runner: LaunchctlRunner | None = None
    python_executable: str = sys.executable
    interval_seconds: int = DAEMON_INTERVAL_SECONDS
    idle_timeout_seconds: int = DAEMON_IDLE_TIMEOUT_SECONDS
    home: Path | None = None


def launchd_rewake_supported(
    env: Mapping[str, str] | None = None,
    *,
    platform_name: str = sys.platform,
) -> bool:
    """Return whether this process can hand waits to launchd rewake."""

    current = os.environ if env is None else env
    return (
        platform_name == "darwin"
        and current.get(CODEX_REWAKE_ENV) == "1"
        and _thread_id(current) != ""
        and codex_binary(current) != ""
    )


def ensure_wait_daemon(
    root: Path,
    wait_id: str,
    *,
    env: Mapping[str, str] | None = None,
    options: LaunchAgentInstallOptions | None = None,
) -> DaemonLaunch:
    """Write rewake envelope and ensure launchd daemon is running."""

    current = os.environ if env is None else env
    label = launchd_label(root)
    log_path = daemon_log_path(root)
    if not launchd_rewake_supported(current):
        return DaemonLaunch(False, label=label, log_path=log_path, error="unsupported")
    try:
        _write_envelope_and_install(
            root,
            wait_id,
            current,
            options=options,
        )
    except (OSError, RuntimeError) as exc:
        return DaemonLaunch(False, label=label, log_path=log_path, error=str(exc))
    return DaemonLaunch(True, label=label, log_path=log_path)


def launch_wait_watcher_process(
    root: Path,
    wait_id: str,
    *,
    python_executable: str | None = None,
) -> tuple[tuple[str, ...], int]:
    """Launch a detached local watcher and return its command and pid."""

    command = (
        python_executable or sys.executable,
        "-m",
        "agent_maintainer",
        "wait",
        "sweep",
        "--watch",
        wait_id,
        "--root",
        str(root),
    )
    process = subprocess.Popen(  # nosec B603 # pylint: disable=consider-using-with
        list(command),
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        start_new_session=True,
    )
    return command, process.pid


def install_launch_agent(
    root: Path,
    *,
    options: LaunchAgentInstallOptions | None = None,
) -> DaemonLaunch:
    """Create and bootstrap LaunchAgent for one repo."""

    install_options = LaunchAgentInstallOptions() if options is None else options
    resolved = root.resolve()
    label = launchd_label(resolved)
    plist_path = launch_agent_path(label, home=install_options.home)
    log_path = daemon_log_path(resolved)
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    write_launch_agent_plist(
        LaunchAgentPlist(
            path=plist_path,
            root=resolved,
            label=label,
            log_path=log_path,
            python_executable=install_options.python_executable,
            interval_seconds=install_options.interval_seconds,
            idle_timeout_seconds=install_options.idle_timeout_seconds,
        ),
    )
    active_runner = (
        _default_launchctl_runner if install_options.runner is None else install_options.runner
    )
    _bootstrap_launch_agent(active_runner, label, plist_path)
    return DaemonLaunch(True, label=label, log_path=log_path)


def uninstall_launch_agent(
    root: Path,
    *,
    runner: LaunchctlRunner | None = None,
    home: Path | None = None,
) -> DaemonStatus:
    """Boot out and remove LaunchAgent for one repo."""

    label = launchd_label(root)
    plist_path = launch_agent_path(label, home=home)
    active_runner = _default_launchctl_runner if runner is None else runner
    _run_ignoring_missing(active_runner, ("launchctl", "bootout", launchd_service(label)))
    plist_path.unlink(missing_ok=True)
    return daemon_status(root, runner=active_runner, home=home)


def daemon_status(
    root: Path,
    *,
    runner: LaunchctlRunner | None = None,
    home: Path | None = None,
) -> DaemonStatus:
    """Return launchd status for one repo wait daemon."""

    label = launchd_label(root)
    active_runner = _default_launchctl_runner if runner is None else runner
    result = active_runner(("launchctl", "print", launchd_service(label)))
    heartbeat = read_heartbeat(root)
    plist_path = launch_agent_path(label, home=home)
    log_path = daemon_log_path(root)
    if result.returncode != 0:
        return DaemonStatus(
            label=label,
            plist_path=plist_path,
            log_path=log_path,
            loaded=False,
            last_heartbeat=heartbeat,
            error=_completed_error(result),
        )
    return DaemonStatus(
        label=label,
        plist_path=plist_path,
        log_path=log_path,
        loaded=True,
        pid=_pid_from_launchctl(result.stdout),
        last_heartbeat=heartbeat,
    )


def launchd_label(root: Path) -> str:
    """Return stable LaunchAgent label for repo root."""

    digest = hashlib.sha256(str(root.resolve()).encode("utf-8")).hexdigest()[:LABEL_HASH_LENGTH]
    return f"{LAUNCHD_LABEL_PREFIX}.{digest}"


def launch_agent_path(label: str, *, home: Path | None = None) -> Path:
    """Return user LaunchAgent plist path for label."""

    root = Path.home() if home is None else home
    return root / "Library" / "LaunchAgents" / f"{label}.plist"


def launchd_service(label: str) -> str:
    """Return launchctl service target for label."""

    return f"gui/{os.getuid()}/{label}"


def status_text(status: DaemonStatus) -> str:
    """Render daemon status compact text."""

    loaded = "loaded" if status.loaded else "not loaded"
    lines = [
        f"Result: {loaded}",
        f"Label: {status.label}",
        f"Plist: {status.plist_path}",
        f"Log: {status.log_path}",
    ]
    if status.pid is not None:
        lines.append(f"PID: {status.pid}")
    if status.last_heartbeat:
        lines.append(f"Last heartbeat: {status.last_heartbeat}")
    if status.error:
        lines.append(f"Error: {status.error}")
    return "\n".join(lines)


def _write_envelope_and_install(
    root: Path,
    wait_id: str,
    env: Mapping[str, str],
    *,
    options: LaunchAgentInstallOptions | None,
) -> None:
    write_rewake_envelope(root, wait_id, env)
    install_launch_agent(root, options=options)


def _bootstrap_launch_agent(
    runner: LaunchctlRunner,
    label: str,
    plist_path: Path,
) -> None:
    bootstrap = runner(("launchctl", "bootstrap", f"gui/{os.getuid()}", str(plist_path)))
    if bootstrap.returncode != 0:
        _run_ignoring_missing(runner, ("launchctl", "bootout", launchd_service(label)))
        bootstrap = runner(("launchctl", "bootstrap", f"gui/{os.getuid()}", str(plist_path)))
    if bootstrap.returncode != 0:
        raise RuntimeError(_completed_error(bootstrap))
    kickstart = runner(("launchctl", "kickstart", "-k", launchd_service(label)))
    if kickstart.returncode != 0:
        raise RuntimeError(_completed_error(kickstart))


def _default_launchctl_runner(
    command: Sequence[str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603
        list(command),
        check=False,
        text=True,
        capture_output=True,
    )


def _run_ignoring_missing(runner: LaunchctlRunner, command: Sequence[str]) -> None:
    runner(command)


def _thread_id(env: Mapping[str, str]) -> str:
    return env.get("AGENT_MAINTAINER_CODEX_THREAD_ID") or env.get("CODEX_THREAD_ID", "")


def _completed_error(result: subprocess.CompletedProcess[str]) -> str:
    return (result.stderr or result.stdout or f"exit {result.returncode}").strip()


def _pid_from_launchctl(output: str) -> int | None:
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("pid = "):
            return int(stripped.removeprefix("pid = "))
    return None
