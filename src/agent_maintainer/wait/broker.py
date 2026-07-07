"""Agent Maintainer background wait broker adapters."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Final

from agent_maintainer.wait.registry import RegisterGitHubPrWait, WaitRegistry
from agent_maintainer.wait.sweeper import start_wait_watcher
from agent_waits import broker as wait_broker

CODEX_BACKGROUND_PR_WAIT_ENV: Final = "AGENT_MAINTAINER_BACKGROUND_PR_WAIT"
CODEX_ALLOW_FOREGROUND_WAIT_ENV = wait_broker.CODEX_ALLOW_FOREGROUND_WAIT_ENV
CODEX_ENV_MARKERS = wait_broker.CODEX_ENV_MARKERS
CODEX_PLATFORM = wait_broker.CODEX_PLATFORM
BACKGROUND_PR_WAIT_FLAGS: Final[Mapping[str | None, bool]] = MappingProxyType({"0": False})
BackgroundWaitRegistration = wait_broker.BackgroundWaitRegistration
codex_foreground_wait_allowed = wait_broker.codex_foreground_wait_allowed
heartbeat_prompt = wait_broker.heartbeat_prompt
render_background_registration_text = wait_broker.render_background_registration_text
running_in_codex = wait_broker.running_in_codex


@dataclass(frozen=True)
class BackgroundGitHubPrWait:
    """Inputs for registering one background GitHub PR wait."""

    root: Path
    pr_number: str
    repo: str | None
    platform: str = CODEX_PLATFORM
    interval_seconds: int = 20
    timeout_seconds: int = 3600


def register_background_github_pr(wait: BackgroundGitHubPrWait) -> BackgroundWaitRegistration:
    """Register a GitHub PR wait with a silent watcher."""

    record = WaitRegistry(wait.root).register_github_pr(
        RegisterGitHubPrWait(
            root=wait.root,
            pr_number=wait.pr_number,
            repo=wait.repo,
            platform=wait.platform,
            interval_seconds=wait.interval_seconds,
            timeout_seconds=wait.timeout_seconds,
        ),
    )
    try:
        start_wait_watcher(wait.root, record.wait_id)
    except OSError as exc:
        return BackgroundWaitRegistration(
            record=record,
            watcher_started=False,
            watcher_error=str(exc),
        )
    return BackgroundWaitRegistration(record=record, watcher_started=True)


def codex_background_pr_wait_enabled(env: Mapping[str, str] | None = None) -> bool:
    """Return whether Codex PR waits should register background waits."""

    if env is None:
        return _codex_background_pr_wait_enabled(os.environ)
    return _codex_background_pr_wait_enabled(env)


def _codex_background_pr_wait_enabled(current: Mapping[str, str]) -> bool:
    if current.get(CODEX_ALLOW_FOREGROUND_WAIT_ENV) == "1":
        return False
    return BACKGROUND_PR_WAIT_FLAGS.get(current.get(CODEX_BACKGROUND_PR_WAIT_ENV), True)
