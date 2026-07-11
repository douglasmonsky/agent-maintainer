"""Durable lifecycle state for detached verifier processes."""

from __future__ import annotations

import json
import time
from contextlib import suppress
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Final
from uuid import uuid4

from agent_maintainer.core.structured_values import json_array, json_object

JOB_STATUS_STARTING: Final = "starting"
JOB_STATUS_RUNNING: Final = "running"
JOB_STATUS_PASSED: Final = "passed"
JOB_STATUS_FAILED: Final = "failed"
JOB_STATUS_ERROR: Final = "error"
JOB_STATUS_CANCELLED: Final = "cancelled"
LEGACY_JOB_STATUS_STARTED: Final = "started"
TERMINAL_JOB_STATUSES: Final = frozenset(
    (JOB_STATUS_PASSED, JOB_STATUS_FAILED, JOB_STATUS_ERROR, JOB_STATUS_CANCELLED),
)
VALID_JOB_STATUSES: Final = TERMINAL_JOB_STATUSES | frozenset(
    (JOB_STATUS_STARTING, JOB_STATUS_RUNNING, LEGACY_JOB_STATUS_STARTED),
)


@dataclass(frozen=True)
class AsyncVerifierState:
    """Persisted lifecycle state for one async verifier process."""

    run_id: str
    profile: str
    status: str
    process_id: int
    command: tuple[str, ...]
    fingerprint: dict[str, object]
    stdout_path: str
    stderr_path: str
    started_at: float
    updated_at: float
    exit_code: int | None = None
    error: str = ""
    phase: str = "launch"

    @property
    def terminal(self) -> bool:
        """Return whether the job has a durable terminal state."""

        return self.status in TERMINAL_JOB_STATUSES


class AsyncVerifierStateError(ValueError):
    """Persisted async verifier state is malformed or unavailable."""


def read_async_state(state_path: Path) -> AsyncVerifierState | None:
    """Read one async job state, returning ``None`` when it does not exist."""

    try:
        decoded: object = json.loads(state_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as exc:
        raise AsyncVerifierStateError(f"cannot read async state {state_path}: {exc}") from exc
    payload = json_object(decoded)
    if payload is None:
        raise AsyncVerifierStateError(f"async state is not an object: {state_path}")
    try:
        return _state_from_payload(payload)
    except (KeyError, TypeError, ValueError) as exc:
        raise AsyncVerifierStateError(f"invalid async state {state_path}: {exc}") from exc


def _state_payload(state: AsyncVerifierState) -> dict[str, object]:
    return {
        "run_id": state.run_id,
        "profile": state.profile,
        "status": state.status,
        "process_id": state.process_id,
        "command": list(state.command),
        "fingerprint": state.fingerprint,
        "stdout_path": state.stdout_path,
        "stderr_path": state.stderr_path,
        "started_at": state.started_at,
        "updated_at": state.updated_at,
        "exit_code": state.exit_code,
        "error": state.error,
        "phase": state.phase,
    }


def write_async_state(state_path: Path, state: AsyncVerifierState) -> None:
    """Atomically persist one async verifier state."""

    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _state_payload(state)
    tmp_path = state_path.with_name(f".{state_path.name}.{uuid4().hex}.tmp")
    try:
        _replace_state(tmp_path, state_path, payload)
    except OSError:
        with suppress(OSError):
            tmp_path.unlink()
        raise


def mark_async_running(state_path: Path, *, process_id: int) -> AsyncVerifierState:
    """Persist the child PID after successful process creation."""

    state = _required_state(state_path)
    if state.terminal:
        return state
    running = replace(
        state,
        status=JOB_STATUS_RUNNING,
        process_id=process_id,
        updated_at=time.time(),
        phase="verify",
    )
    write_async_state(state_path, running)
    return running


def mark_async_terminal(
    state_path: Path,
    *,
    status: str,
    exit_code: int | None,
    error: str = "",
    phase: str = "verify",
) -> AsyncVerifierState:
    """Persist an explicit terminal process outcome."""

    if status not in TERMINAL_JOB_STATUSES:
        raise AsyncVerifierStateError(f"invalid terminal async status: {status}")
    state = _required_state(state_path)
    terminal = replace(
        state,
        status=status,
        exit_code=exit_code,
        error=error,
        phase=phase,
        updated_at=time.time(),
    )
    write_async_state(state_path, terminal)
    return terminal


def _replace_state(
    tmp_path: Path,
    state_path: Path,
    payload: dict[str, object],
) -> None:
    tmp_path.write_text(f"{json.dumps(payload, sort_keys=True)}\n", encoding="utf-8")
    tmp_path.replace(state_path)


def _state_from_payload(payload: dict[str, object]) -> AsyncVerifierState:
    exit_code = _optional_exit_code(payload.get("exit_code"))
    fingerprint = _strict_mapping(payload.get("fingerprint", {}), "fingerprint")
    command = _strict_command(payload.get("command", []))
    status = _strict_status(payload.get("status", LEGACY_JOB_STATUS_STARTED))
    return AsyncVerifierState(
        run_id=str(payload["run_id"]),
        profile=str(payload.get("profile", "")),
        status=status,
        process_id=_strict_int(payload.get("process_id", 0), "process_id"),
        command=tuple(command),
        fingerprint=fingerprint,
        stdout_path=str(payload.get("stdout_path", "")),
        stderr_path=str(payload.get("stderr_path", "")),
        started_at=_strict_float(payload.get("started_at", 0), "started_at"),
        updated_at=_strict_float(payload.get("updated_at", 0), "updated_at"),
        exit_code=exit_code,
        error=str(payload.get("error", "")),
        phase=str(payload.get("phase", "")),
    )


def _optional_exit_code(value: object) -> int | None:
    if value is None:
        return None
    return _strict_int(value, "exit_code")


def _strict_mapping(value: object, field_name: str) -> dict[str, object]:
    mapping = json_object(value)
    if mapping is None:
        raise TypeError(f"{field_name} must be an object")
    return mapping


def _strict_command(value: object) -> list[str]:
    values = json_array(value)
    if values is None or not all(isinstance(item, str) for item in values):
        raise TypeError("command must be an array of strings")
    return [item for item in values if isinstance(item, str)]


def _strict_status(value: object) -> str:
    status = str(value)
    if status not in VALID_JOB_STATUSES:
        raise ValueError(f"unknown async status: {status}")
    return status


def _strict_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    return value


def _strict_float(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be numeric")
    return float(value)


def _required_state(state_path: Path) -> AsyncVerifierState:
    state = read_async_state(state_path)
    if state is None:
        raise AsyncVerifierStateError(f"async state not found: {state_path}")
    return state
