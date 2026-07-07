"""Background wait broker for Codex-safe long-running waits."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from agent_maintainer.wait.models import WaitRepairCapsule, render_wait_capsule
from agent_maintainer.wait.registry import RegisterGitHubPrWait, WaitRecord, WaitRegistry
from agent_maintainer.wait.sweeper import start_wait_watcher

CODEX_PLATFORM: Final = "codex"
CODEX_BACKGROUND_PR_WAIT_ENV: Final = "AGENT_MAINTAINER_BACKGROUND_PR_WAIT"
CODEX_ALLOW_FOREGROUND_WAIT_ENV: Final = "AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT"
CODEX_ENV_MARKERS: Final = ("CODEX_SHELL", "CODEX_THREAD_ID")


@dataclass(frozen=True)
class BackgroundGitHubPrWait:
    """Inputs for registering one background GitHub PR wait."""

    root: Path
    pr_number: str
    repo: str | None
    platform: str = CODEX_PLATFORM
    interval_seconds: int = 20
    timeout_seconds: int = 3600


@dataclass(frozen=True)
class BackgroundWaitRegistration:
    """Result from registering a wait for background ownership."""

    record: WaitRecord
    watcher_started: bool
    watcher_error: str = ""


def register_background_github_pr(wait: BackgroundGitHubPrWait) -> BackgroundWaitRegistration:
    """Register a GitHub PR wait and try to start a silent watcher."""

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
    """Return whether Codex PR waits should use background ownership."""

    values = os.environ if env is None else env
    if values.get(CODEX_ALLOW_FOREGROUND_WAIT_ENV) == "1":
        return False
    return values.get(CODEX_BACKGROUND_PR_WAIT_ENV, "1") != "0"


def codex_foreground_wait_allowed(env: Mapping[str, str] | None = None) -> bool:
    """Return whether foreground wait polling is explicitly allowed in Codex."""

    values = os.environ if env is None else env
    return values.get(CODEX_ALLOW_FOREGROUND_WAIT_ENV) == "1"


def running_in_codex(env: Mapping[str, str] | None = None) -> bool:
    """Return whether the current process looks like a Codex-run command."""

    values = os.environ if env is None else env
    return any(values.get(name) for name in CODEX_ENV_MARKERS)


def render_background_registration_text(registration: BackgroundWaitRegistration) -> str:
    """Render one compact background-wait handoff for humans and agents."""

    resume_instruction = registration.record.resume_instruction
    details = (
        _wait_detail(registration.record),
        _watcher_detail(registration),
        f"manual resume: {resume_instruction}",
        f"heartbeat prompt: {heartbeat_prompt(registration.record)}",
    )
    return render_wait_capsule(
        WaitRepairCapsule(
            result="PENDING",
            run_id=registration.record.wait_id,
            details=details,
        ),
    )


def heartbeat_prompt(record: WaitRecord) -> str:
    """Return the Codex heartbeat prompt for a registered wait."""

    return (
        f"Sweep wait {record.wait_id}. If it is still pending, stay silent and "
        "let the next heartbeat continue polling. If terminal, render the wait "
        "resume capsule, inspect failures if any, merge only if satisfactory, "
        "then continue the prior roadmap task."
    )


def _wait_detail(record: WaitRecord) -> str:
    repo = f" repo={record.repo}" if record.repo else ""
    return f"{record.kind} pr={record.pr_number} platform={record.platform}{repo}"


def _watcher_detail(registration: BackgroundWaitRegistration) -> str:
    if registration.watcher_started:
        return "watcher: started"
    return f"watcher: not started ({registration.watcher_error})"
