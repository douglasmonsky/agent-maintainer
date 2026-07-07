"""Codex-safe background wait handoff helpers."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from agent_waits.models import WaitRepairCapsule, render_wait_capsule
from agent_waits.registry import WaitRecord

CODEX_PLATFORM: Final = "codex"
CODEX_ALLOW_FOREGROUND_WAIT_ENV: Final = "AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT"
CODEX_ENV_MARKERS: Final = ("CODEX_SHELL", "CODEX_THREAD_ID")
HEARTBEAT_REQUEST_TYPE: Final = "codex_heartbeat_wait"


@dataclass(frozen=True)
class BackgroundWaitRegistration:
    """Result registering background wait ownership."""

    record: WaitRecord
    watcher_started: bool
    watcher_error: str = ""
    root: str = ""


def codex_foreground_wait_allowed(env: Mapping[str, str] | None = None) -> bool:
    """Return whether Codex may run a foreground long wait."""

    return _codex_foreground_wait_allowed(os.environ if env is None else env)


def running_in_codex(env: Mapping[str, str] | None = None) -> bool:
    """Return whether current process appears to run inside Codex."""

    return _running_in_codex(os.environ if env is None else env)


def render_background_registration_text(
    registration: BackgroundWaitRegistration,
) -> str:
    """Render compact background wait registration handoff."""

    record = registration.record
    return render_wait_capsule(
        WaitRepairCapsule(
            result=record.terminal_result if record.ready else "PENDING",
            run_id=record.wait_id,
            details=(
                _wait_detail(record),
                _watcher_detail(registration),
                f"manual resume: {record.resume_instruction}",
                "heartbeat request:",
                heartbeat_request_json(record, root=registration.root),
            ),
        ),
    )


def heartbeat_prompt(record: WaitRecord) -> str:
    """Return Codex heartbeat prompt for one durable wait."""

    if record.kind == "github-pr":
        return (
            f"Sweep wait {record.wait_id}. If it is still pending, stay silent and "
            "let the next heartbeat continue polling. If terminal, render the wait "
            "resume capsule, inspect failures if any, merge only if satisfactory, "
            "then continue the prior roadmap task."
        )
    if record.kind == "github-run":
        return (
            f"Sweep wait {record.wait_id}. If it is still pending, stay silent and "
            "let the next heartbeat continue polling. If terminal, render the wait "
            "resume capsule, inspect failed jobs if any, then continue the prior task."
        )
    if record.kind == "verifier":
        return (
            f"Sweep wait {record.wait_id}. If it is still pending, stay silent and "
            "let the next heartbeat continue polling. If terminal, render the wait "
            "resume capsule, inspect failed checks if any, then continue the prior task."
        )
    return (
        f"Sweep wait {record.wait_id}. If it is still pending, stay silent and let "
        "the next heartbeat continue polling. If terminal, render the wait resume "
        "capsule and continue the prior task."
    )


def heartbeat_request(
    record: WaitRecord,
    *,
    root: str | Path = "",
) -> dict[str, object]:
    """Return machine-readable Codex heartbeat creation request."""

    root_text = str(root)
    sweep_command = "python -m agent_maintainer wait heartbeat"
    resume_command = record.resume_instruction
    if root_text:
        sweep_command = f"{sweep_command} --root {root_text}"
        resume_command = f"{resume_command} --root {root_text}"
    return {
        "type": HEARTBEAT_REQUEST_TYPE,
        "wait_id": record.wait_id,
        "wait_kind": record.kind,
        "scope": "repo",
        "target_id": record.target_id,
        "repo": record.repo,
        "root": root_text,
        "sweep_command": sweep_command,
        "resume_command": resume_command,
        "prompt": heartbeat_prompt(record),
    }


def heartbeat_request_json(
    record: WaitRecord,
    *,
    root: str | Path = "",
) -> str:
    """Render machine-readable Codex heartbeat request JSON."""

    return json.dumps(heartbeat_request(record, root=root), sort_keys=True)


def _wait_detail(record: WaitRecord) -> str:
    return f"{record.kind} wait registered for {record.target_id}."


def _watcher_detail(registration: BackgroundWaitRegistration) -> str:
    if registration.watcher_started:
        return "watcher: started"
    if registration.watcher_error:
        return f"watcher: not started ({registration.watcher_error})"
    return "watcher: not started"


def _codex_foreground_wait_allowed(env: Mapping[str, str]) -> bool:
    return env.get(CODEX_ALLOW_FOREGROUND_WAIT_ENV) == "1"


def _running_in_codex(env: Mapping[str, str]) -> bool:
    return any(env.get(marker) for marker in CODEX_ENV_MARKERS)
