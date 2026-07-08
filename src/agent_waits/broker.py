"""Codex-safe background wait handoff helpers."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from shutil import which
from types import MappingProxyType
from typing import Final

from agent_waits.models import WaitRepairCapsule, render_wait_capsule
from agent_waits.registry import WaitRecord

CODEX_PLATFORM: Final = "codex"
CODEX_ALLOW_FOREGROUND_WAIT_ENV: Final = "AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT"
CODEX_BACKGROUND_WAIT_ENV: Final = "AGENT_MAINTAINER_BACKGROUND_WAIT"
CODEX_REWAKE_ENV: Final = "AGENT_MAINTAINER_CODEX_REWAKE"
CODEX_BIN_ENV: Final = "AGENT_MAINTAINER_CODEX_BIN"
CODEX_THREAD_ID_ENV: Final = "CODEX_THREAD_ID"
CODEX_THREAD_ID_OVERRIDE_ENV: Final = "AGENT_MAINTAINER_CODEX_THREAD_ID"
CODEX_ENV_MARKERS: Final = (
    "CODEX_SHELL",
    CODEX_THREAD_ID_ENV,
    CODEX_THREAD_ID_OVERRIDE_ENV,
)
CHEAP_MONITOR_MODEL: Final = "gpt-5.3-codex-spark"
HEARTBEAT_DEFAULT_INTERVAL_SECONDS: Final = 120
HEARTBEAT_REQUEST_TYPE: Final = "codex_heartbeat_wait"
OPENAI_CODEX_PACKAGE: Final = "openai_codex"
CODEX_CLI_NAME: Final = "codex"
BACKGROUND_WAIT_FLAGS: Final[Mapping[str | None, bool]] = MappingProxyType({"0": False})


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


def codex_background_wait_enabled(env: Mapping[str, str] | None = None) -> bool:
    """Return whether Codex background wait registration is enabled."""

    return _codex_background_wait_enabled(os.environ if env is None else env)


def codex_terminal_rewake_available(
    registration: BackgroundWaitRegistration,
    *,
    env: Mapping[str, str] | None = None,
    sdk_available: bool | None = None,
) -> bool:
    """Return whether detached watcher can wake Codex on terminal state."""

    current = os.environ if env is None else env
    return _codex_terminal_context_available(
        registration,
        current,
    ) and _codex_rewake_backend_available(sdk_available, current)


def render_background_registration_text(
    registration: BackgroundWaitRegistration,
    *,
    env: Mapping[str, str] | None = None,
    sdk_available: bool | None = None,
) -> str:
    """Render compact background wait registration handoff."""

    record = registration.record
    if codex_terminal_rewake_available(
        registration,
        env=env,
        sdk_available=sdk_available,
    ):
        return render_wait_capsule(
            WaitRepairCapsule(
                result=record.terminal_result if record.ready else "PENDING",
                run_id=record.wait_id,
                details=(
                    _wait_detail(record),
                    "watcher: started; pending polls stay outside model turns",
                    "terminal rewake: enabled for this Codex thread",
                    f"manual fallback resume: {record.resume_instruction}",
                ),
            ),
        )

    return render_wait_capsule(
        WaitRepairCapsule(
            result=record.terminal_result if record.ready else "PENDING",
            run_id=record.wait_id,
            details=(
                _wait_detail(record),
                _watcher_detail(registration),
                f"manual resume: {record.resume_instruction}",
                "fallback heartbeat request:",
                heartbeat_request_json(record, root=registration.root),
            ),
        ),
    )


def heartbeat_prompt(_record: WaitRecord) -> str:
    """Return Codex heartbeat prompt for a targeted wait sweep."""

    return (
        "Run the targeted wait sweep command from this request. "
        "If it prints nothing, stay silent and let the next heartbeat continue "
        "polling. If it prints a terminal resume capsule, inspect failures if "
        "any, merge only if satisfactory, then continue prior task."
    )


def heartbeat_request(
    record: WaitRecord,
    *,
    root: str | Path = "",
) -> dict[str, object]:
    """Return machine-readable Codex heartbeat creation request."""

    root_text = str(root)
    sweep_command = f"python -m agent_maintainer wait sweep --one {record.wait_id}"
    resume_command = record.resume_instruction
    if root_text:
        sweep_command = f"{sweep_command} --root {root_text}"
        resume_command = f"{resume_command} --root {root_text}"
    return {
        "type": HEARTBEAT_REQUEST_TYPE,
        "wait_id": record.wait_id,
        "wait_kind": record.kind,
        "scope": "wait",
        "target_id": record.target_id,
        "repo": record.repo,
        "root": root_text,
        "sweep_command": sweep_command,
        "resume_command": resume_command,
        "on_pending": "silent",
        "on_terminal": "resume_and_review",
        "fallback_only": True,
        "preferred_monitor_model": CHEAP_MONITOR_MODEL,
        "preferred_monitor_reasoning": "minimal",
        "preferred_interval_seconds": max(
            record.interval_seconds,
            HEARTBEAT_DEFAULT_INTERVAL_SECONDS,
        ),
        "merge_policy": "merge_only_if_satisfactory",
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


def _codex_background_wait_enabled(env: Mapping[str, str]) -> bool:
    return BACKGROUND_WAIT_FLAGS.get(env.get(CODEX_BACKGROUND_WAIT_ENV), True)


def _running_in_codex(env: Mapping[str, str]) -> bool:
    return any(env.get(marker) for marker in CODEX_ENV_MARKERS)


def _codex_thread_id(env: Mapping[str, str]) -> str:
    return env.get(CODEX_THREAD_ID_OVERRIDE_ENV) or env.get(CODEX_THREAD_ID_ENV, "")


def _codex_terminal_context_available(
    registration: BackgroundWaitRegistration,
    env: Mapping[str, str],
) -> bool:
    return (
        registration.watcher_started
        and registration.record.platform == CODEX_PLATFORM
        and env.get(CODEX_REWAKE_ENV) == "1"
        and _codex_thread_id(env) != ""
    )


def _codex_rewake_backend_available(
    sdk_available: bool | None,
    env: Mapping[str, str],
) -> bool:
    if sdk_available is not None:
        return sdk_available
    return bool(env.get(CODEX_BIN_ENV) or which(CODEX_CLI_NAME) or find_spec(OPENAI_CODEX_PACKAGE))
