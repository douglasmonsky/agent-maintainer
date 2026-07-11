"""Agent Maintainer background wait broker adapters."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Final

from agent_maintainer.wait import (
    daemon_launchd,
    handlers,
)
from agent_maintainer.wait import (
    registry as wait_registry,
)
from agent_waits import broker as wait_broker
from agent_waits import watcher_state as wait_watcher_state

CODEX_BACKGROUND_PR_WAIT_ENV: Final = "AGENT_MAINTAINER_BACKGROUND_PR_WAIT"
CODEX_BACKGROUND_WAIT_ENV: Final = "AGENT_MAINTAINER_BACKGROUND_WAIT"
CODEX_ALLOW_FOREGROUND_WAIT_ENV = wait_broker.CODEX_ALLOW_FOREGROUND_WAIT_ENV
CODEX_ENV_MARKERS = wait_broker.CODEX_ENV_MARKERS
CODEX_PLATFORM = wait_broker.CODEX_PLATFORM
BACKGROUND_WAIT_FLAGS: Final[Mapping[str | None, bool]] = MappingProxyType({"0": False})

ensure_wait_daemon = daemon_launchd.ensure_wait_daemon
handler_for = handlers.handler_for
WaitRegistration = handlers.WaitRegistration
WAIT_KIND_GITHUB_PR = wait_registry.WAIT_KIND_GITHUB_PR
WAIT_KIND_GITHUB_RUN = wait_registry.WAIT_KIND_GITHUB_RUN
WAIT_KIND_VERIFIER = wait_registry.WAIT_KIND_VERIFIER
WaitRecord = wait_registry.WaitRecord
WaitRegistry = wait_registry.WaitRegistry

BackgroundWaitRegistration = wait_broker.BackgroundWaitRegistration
codex_foreground_wait_allowed = wait_broker.codex_foreground_wait_allowed
codex_terminal_rewake_available = wait_broker.codex_terminal_rewake_available
heartbeat_prompt = wait_broker.heartbeat_prompt
heartbeat_backoff = wait_broker.heartbeat_backoff
heartbeat_request = wait_broker.heartbeat_request
heartbeat_request_json = wait_broker.heartbeat_request_json
render_background_registration_text = wait_broker.render_background_registration_text
running_in_codex = wait_broker.running_in_codex


@dataclass(frozen=True)
class BackgroundKnownWait:
    """Inputs registering one known background wait."""

    root: Path
    kind: str
    target_id: str
    repo: str | None = None
    platform: str = CODEX_PLATFORM
    branch: str = ""
    head_sha: str = ""
    log_dir: Path = Path(".verify-logs")
    interval_seconds: int = 20
    timeout_seconds: int = 3600


@dataclass(frozen=True)
class BackgroundGitHubPrWait:
    """Inputs registering one background GitHub PR wait."""

    root: Path
    pr_number: str
    repo: str | None
    platform: str = CODEX_PLATFORM
    interval_seconds: int = 20
    timeout_seconds: int = 3600


@dataclass(frozen=True)
class BackgroundGitHubRunWait:
    """Inputs registering one background GitHub run wait."""

    root: Path
    run_id: str
    repo: str | None
    platform: str = CODEX_PLATFORM
    interval_seconds: int = 20
    timeout_seconds: int = 3600


@dataclass(frozen=True)
class BackgroundVerifierWait:
    """Inputs registering one background verifier wait."""

    root: Path
    run_id: str
    platform: str = CODEX_PLATFORM
    log_dir: Path = Path(".verify-logs")
    interval_seconds: int = 5
    timeout_seconds: int = 3600


@dataclass(frozen=True)
class DetachedWatcher:
    """Detached watcher metadata."""

    command: tuple[str, ...]
    pid: int


def start_wait_watcher(
    root: Path,
    wait_id: str,
    *,
    python_executable: str | None = None,
) -> DetachedWatcher:
    """Start a detached local watcher process for one wait record."""

    command, pid = daemon_launchd.launch_wait_watcher_process(
        root,
        wait_id,
        python_executable=python_executable,
    )
    return DetachedWatcher(command=command, pid=pid)


def register_background_wait(wait: BackgroundKnownWait) -> BackgroundWaitRegistration:
    """Register a known wait and start its silent watcher."""

    registry = WaitRegistry(wait.root)
    record = handler_for(wait.kind).register(
        registry,
        WaitRegistration(
            root=wait.root,
            target_id=wait.target_id,
            repo=wait.repo,
            platform=wait.platform,
            branch=wait.branch,
            head_sha=wait.head_sha,
            interval_seconds=wait.interval_seconds,
            timeout_seconds=wait.timeout_seconds,
            log_dir=wait.log_dir,
        ),
    )
    return start_registered_watcher(wait.root, record)


def start_registered_watcher(root: Path, record: WaitRecord) -> BackgroundWaitRegistration:
    """Start the strongest available watcher for an existing wait record."""

    daemon_launch = ensure_wait_daemon(root, record.wait_id)
    if daemon_launch.started:
        updated = wait_watcher_state.mark_watcher_started(
            WaitRegistry(root),
            record,
            strategy="launchd",
            pid=None,
        )
        return BackgroundWaitRegistration(
            record=updated,
            watcher_started=True,
            root=str(root),
            watcher_strategy="launchd",
            watcher_label=daemon_launch.label,
            watcher_log=str(daemon_launch.log_path),
        )
    if _strict_codex_rewake(record):
        updated = wait_watcher_state.mark_watcher_failed(
            WaitRegistry(root),
            record,
            error_code="launchd_required",
        )
        return BackgroundWaitRegistration(
            record=updated,
            watcher_started=False,
            watcher_error=f"launchd required for Codex rewake: {daemon_launch.error}",
            root=str(root),
            watcher_strategy="",
        )

    try:
        watcher = start_wait_watcher(root, record.wait_id)
    except OSError as exc:
        watcher_error = str(exc)
        if daemon_launch.error and daemon_launch.error != "unsupported":
            watcher_error = f"launchd: {daemon_launch.error}; popen: {watcher_error}"
        updated = wait_watcher_state.mark_watcher_failed(
            WaitRegistry(root),
            record,
            error_code="watcher_start_failed",
        )
        return BackgroundWaitRegistration(
            record=updated,
            watcher_started=False,
            watcher_error=watcher_error,
            root=str(root),
        )

    watcher_error = ""
    if daemon_launch.error and daemon_launch.error != "unsupported":
        watcher_error = f"launchd fallback: {daemon_launch.error}"
    updated = wait_watcher_state.mark_watcher_started(
        WaitRegistry(root),
        record,
        strategy="popen",
        pid=watcher.pid,
    )
    return BackgroundWaitRegistration(
        record=updated,
        watcher_started=True,
        watcher_error=watcher_error,
        root=str(root),
        watcher_strategy="popen",
        watcher_pid=watcher.pid,
    )


def _strict_codex_rewake(record: WaitRecord) -> bool:
    return record.platform == CODEX_PLATFORM


def register_background_github_pr(
    wait: BackgroundGitHubPrWait,
) -> BackgroundWaitRegistration:
    """Register GitHub PR wait with a silent watcher."""

    return register_background_wait(
        BackgroundKnownWait(
            root=wait.root,
            kind=WAIT_KIND_GITHUB_PR,
            target_id=wait.pr_number,
            repo=wait.repo,
            platform=wait.platform,
            interval_seconds=wait.interval_seconds,
            timeout_seconds=wait.timeout_seconds,
        ),
    )


def register_background_github_run(
    wait: BackgroundGitHubRunWait,
) -> BackgroundWaitRegistration:
    """Register GitHub run wait with a silent watcher."""

    return register_background_wait(
        BackgroundKnownWait(
            root=wait.root,
            kind=WAIT_KIND_GITHUB_RUN,
            target_id=wait.run_id,
            repo=wait.repo,
            platform=wait.platform,
            interval_seconds=wait.interval_seconds,
            timeout_seconds=wait.timeout_seconds,
        ),
    )


def register_background_verifier(wait: BackgroundVerifierWait) -> BackgroundWaitRegistration:
    """Register verifier wait with a silent watcher."""

    return register_background_wait(
        BackgroundKnownWait(
            root=wait.root,
            kind=WAIT_KIND_VERIFIER,
            target_id=wait.run_id,
            platform=wait.platform,
            log_dir=wait.log_dir,
            interval_seconds=wait.interval_seconds,
            timeout_seconds=wait.timeout_seconds,
        ),
    )


def codex_background_wait_enabled(env: Mapping[str, str] | None = None) -> bool:
    """Return whether Codex background wait registration is enabled."""

    current = os.environ if env is None else env
    return BACKGROUND_WAIT_FLAGS.get(current.get(CODEX_BACKGROUND_WAIT_ENV), True)


def codex_background_pr_wait_enabled(env: Mapping[str, str] | None = None) -> bool:
    """Return whether Codex PR waits should register background wait records."""

    current = os.environ if env is None else env
    if not codex_background_wait_enabled(current):
        return False
    return BACKGROUND_WAIT_FLAGS.get(current.get(CODEX_BACKGROUND_PR_WAIT_ENV), True)
