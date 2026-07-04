"""Async verifier job state helpers."""

from __future__ import annotations

import json
import subprocess  # nosec B404
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

from agent_maintainer.wait.models import WaitRepairCapsule, render_wait_capsule

ASYNC_FLAG: Final = "--async"
JOBS_DIR_NAME: Final = "jobs"
JOB_STATUS_STARTED: Final = "started"


@dataclass(frozen=True)
class AsyncVerifierRequest:
    """Request to start one background verifier."""

    argv: Sequence[str]
    profile: str
    run_id: str
    log_dir: Path
    fingerprint: dict[str, object]


@dataclass(frozen=True)
class AsyncVerifierLaunch:
    """Result from starting one background verifier."""

    run_id: str
    profile: str
    state_path: Path
    process_id: int
    command: tuple[str, ...]


@dataclass(frozen=True)
class AsyncVerifierState:
    """Persisted async verifier job state."""

    launch: AsyncVerifierLaunch
    fingerprint: dict[str, object]
    stdout_path: Path
    stderr_path: Path


PopenFactory = Callable[..., object]


def launch_async_verifier(
    request: AsyncVerifierRequest,
    *,
    popen: PopenFactory = subprocess.Popen,  # nosec B604
) -> AsyncVerifierLaunch:
    """Launch the current verifier command in the background."""
    jobs_dir = request.log_dir / JOBS_DIR_NAME
    jobs_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = jobs_dir / f"{request.run_id}.stdout.log"
    stderr_path = jobs_dir / f"{request.run_id}.stderr.log"
    command = _async_child_command(request.argv, request.run_id)
    with (
        stdout_path.open("wb") as stdout_handle,
        stderr_path.open(
            "wb",
        ) as stderr_handle,
    ):
        process = popen(  # nosec B603
            command,
            stdout=stdout_handle,
            stderr=stderr_handle,
            start_new_session=True,
        )
    launch = AsyncVerifierLaunch(
        run_id=request.run_id,
        profile=request.profile,
        state_path=jobs_dir / f"{request.run_id}.json",
        process_id=_process_id(process),
        command=tuple(command),
    )
    _write_state(
        AsyncVerifierState(
            launch=launch,
            fingerprint=request.fingerprint,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
        ),
    )
    return launch


def render_async_launch(launch: AsyncVerifierLaunch) -> str:
    """Render compact instructions for a background verifier."""
    return render_wait_capsule(
        WaitRepairCapsule(
            result="PENDING",
            profile=launch.profile,
            run_id=launch.run_id,
            details=(f"Process ID: {launch.process_id}",),
            likely_next_action=(f"python -m agent_maintainer wait verifier {launch.run_id}"),
            expand_command=str(launch.state_path),
        ),
    )


def _async_child_command(argv: Sequence[str], run_id: str) -> list[str]:
    return [
        sys.executable,
        "-m",
        "agent_maintainer",
        "verify",
        *[arg for arg in argv if arg != ASYNC_FLAG],
        "--run-id",
        run_id,
    ]


def _process_id(process: object) -> int:
    return int(cast("subprocess.Popen[bytes]", process).pid)


def _write_state(state: AsyncVerifierState) -> None:
    payload: dict[str, object] = {
        "run_id": state.launch.run_id,
        "profile": state.launch.profile,
        "status": JOB_STATUS_STARTED,
        "process_id": state.launch.process_id,
        "started_at": time.time(),
        "command": list(state.launch.command),
        "fingerprint": state.fingerprint,
        "stdout_path": str(state.stdout_path),
        "stderr_path": str(state.stderr_path),
    }
    state.launch.state_path.write_text(
        f"{json.dumps(payload, sort_keys=True)}\n",
        encoding="utf-8",
    )
