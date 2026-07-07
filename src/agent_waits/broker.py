"""Codex-safe background wait handoff helpers."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

from agent_waits.models import WaitRepairCapsule, render_wait_capsule
from agent_waits.registry import WaitRecord

CODEX_PLATFORM: Final = "codex"
CODEX_ALLOW_FOREGROUND_WAIT_ENV: Final = "AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT"
CODEX_ENV_MARKERS: Final = ("CODEX_SHELL", "CODEX_THREAD_ID")


@dataclass(frozen=True)
class BackgroundWaitRegistration:
    """Result of registering background wait ownership."""

    record: WaitRecord
    watcher_started: bool
    watcher_error: str = ""


def codex_foreground_wait_allowed(env: Mapping[str, str] | None = None) -> bool:
    """Return whether Codex may run a foreground long wait."""

    if env is None:
        return _codex_foreground_wait_allowed(os.environ)
    return _codex_foreground_wait_allowed(env)


def running_in_codex(env: Mapping[str, str] | None = None) -> bool:
    """Return whether current process appears to be running inside Codex."""

    if env is None:
        return _running_in_codex(os.environ)
    return _running_in_codex(env)


def render_background_registration_text(registration: BackgroundWaitRegistration) -> str:
    """Render compact background wait registration handoff."""

    record = registration.record
    return render_wait_capsule(
        WaitRepairCapsule(
            result="PENDING",
            run_id=record.wait_id,
            details=(
                _wait_detail(record),
                _watcher_detail(registration),
                f"manual resume: {record.resume_instruction}",
                f"heartbeat prompt: {heartbeat_prompt(record)}",
            ),
        ),
    )


def heartbeat_prompt(record: WaitRecord) -> str:
    """Return Codex heartbeat prompt for one durable wait."""

    return (
        f"Sweep wait {record.wait_id}. If it is still pending, stay silent and let the "
        "next heartbeat continue polling. If terminal, render the wait resume capsule, "
        "inspect failures if any, merge only if satisfactory, then continue the prior "
        "roadmap task."
    )


def _wait_detail(record: WaitRecord) -> str:
    repo = f" repo={record.repo}" if record.repo else ""
    if record.kind == "github-pr":
        return f"{record.kind} pr={record.target_id} platform={record.platform}{repo}"
    return f"{record.kind} target={record.target_id} platform={record.platform}{repo}"


def _watcher_detail(registration: BackgroundWaitRegistration) -> str:
    if registration.watcher_started:
        return "watcher: started"
    return f"watcher: not started ({registration.watcher_error})"


def _codex_foreground_wait_allowed(current: Mapping[str, str]) -> bool:
    return current.get(CODEX_ALLOW_FOREGROUND_WAIT_ENV) == "1"


def _running_in_codex(current: Mapping[str, str]) -> bool:
    return any(current.get(marker) for marker in CODEX_ENV_MARKERS)
