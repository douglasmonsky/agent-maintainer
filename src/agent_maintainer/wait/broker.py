"""Agent Maintainer background wait broker adapters."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Final

from agent_maintainer.wait.handlers import WaitRegistration, handler_for
from agent_maintainer.wait.registry import (
    WAIT_KIND_GITHUB_PR,
    WAIT_KIND_GITHUB_RUN,
    WAIT_KIND_VERIFIER,
    WaitRegistry,
)
from agent_maintainer.wait.sweeper import start_wait_watcher
from agent_waits import broker as wait_broker

CODEX_BACKGROUND_PR_WAIT_ENV: Final = "AGENT_MAINTAINER_BACKGROUND_PR_WAIT"
CODEX_BACKGROUND_WAIT_ENV: Final = "AGENT_MAINTAINER_BACKGROUND_WAIT"
CODEX_ALLOW_FOREGROUND_WAIT_ENV = wait_broker.CODEX_ALLOW_FOREGROUND_WAIT_ENV
CODEX_ENV_MARKERS = wait_broker.CODEX_ENV_MARKERS
CODEX_PLATFORM = wait_broker.CODEX_PLATFORM
BACKGROUND_WAIT_FLAGS: Final[Mapping[str | None, bool]] = MappingProxyType({"0": False})

BackgroundWaitRegistration = wait_broker.BackgroundWaitRegistration
codex_foreground_wait_allowed = wait_broker.codex_foreground_wait_allowed
heartbeat_prompt = wait_broker.heartbeat_prompt
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
    try:
        start_wait_watcher(wait.root, record.wait_id)
    except OSError as exc:
        return BackgroundWaitRegistration(
            record=record,
            watcher_started=False,
            watcher_error=str(exc),
            root=str(wait.root),
        )
    return BackgroundWaitRegistration(record=record, watcher_started=True, root=str(wait.root))


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
