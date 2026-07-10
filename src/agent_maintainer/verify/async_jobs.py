"""Async verifier process lifecycle and durable job state."""

from __future__ import annotations

import subprocess  # nosec B404
import sys
import time
from collections.abc import Callable, Sequence
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Protocol, cast

from agent_maintainer.verify import async_state
from agent_waits.models import WaitRepairCapsule, render_wait_capsule

ASYNC_FLAG: Final = "--async"
RUN_ID_OPTION: Final = "--run-id"
JOBS_DIR_NAME: Final = "jobs"
PROCESS_STOP_TIMEOUT_SECONDS: Final = 2.0
LAUNCH_ERRORS = (OSError, async_state.AsyncVerifierStateError, TypeError, ValueError)
POST_SPAWN_ERRORS = (async_state.AsyncVerifierStateError, TypeError, ValueError)


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
class _PreparedLaunch:
    """Owned paths and command prepared before process creation."""

    state_path: Path
    stdout_path: Path
    stderr_path: Path
    command: list[str]


class AsyncVerifierLaunchError(RuntimeError):
    """An async verifier could not reach durable running state."""

    def __init__(self, message: str, *, state_path: Path) -> None:
        super().__init__(message)
        self.state_path = state_path


class LaunchedProcess(Protocol):
    """Process operations needed for launch cleanup."""

    pid: int

    def terminate(self) -> None:
        """Request graceful process termination."""

    def kill(self) -> None:
        """Force process termination."""

    def wait(self, timeout: float | None = None) -> int:
        """Wait for process termination."""

        raise NotImplementedError


PopenFactory = Callable[..., object]


def launch_async_verifier(
    request: AsyncVerifierRequest,
    *,
    popen: PopenFactory = subprocess.Popen,  # nosec B604
) -> AsyncVerifierLaunch:
    """Launch a detached verifier with owned streams and durable state."""

    state_path = request.log_dir / JOBS_DIR_NAME / f"{request.run_id}.json"
    try:
        prepared = _prepare_launch(request, state_path)
    except OSError as exc:
        raise _launch_error(request, state_path, exc) from exc
    try:
        return _spawn_running(request, prepared, popen)
    except LAUNCH_ERRORS as exc:
        _record_launch_error(state_path, exc)
        raise _launch_error(request, state_path, exc) from exc


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


def _starting_state(
    request: AsyncVerifierRequest,
    command: list[str],
    stdout_path: Path,
    stderr_path: Path,
) -> async_state.AsyncVerifierState:
    now = time.time()
    return async_state.AsyncVerifierState(
        run_id=request.run_id,
        profile=request.profile,
        status=async_state.JOB_STATUS_STARTING,
        process_id=0,
        command=tuple(command),
        fingerprint=request.fingerprint,
        stdout_path=str(stdout_path),
        stderr_path=str(stderr_path),
        started_at=now,
        updated_at=now,
    )


def _prepare_launch(
    request: AsyncVerifierRequest,
    state_path: Path,
) -> _PreparedLaunch:
    jobs_dir = state_path.parent
    jobs_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = jobs_dir / f"{request.run_id}.stdout.log"
    stderr_path = jobs_dir / f"{request.run_id}.stderr.log"
    command = _async_child_command(request.argv, request.run_id, state_path)
    async_state.write_async_state(
        state_path,
        _starting_state(request, command, stdout_path, stderr_path),
    )
    return _PreparedLaunch(
        state_path=state_path,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        command=command,
    )


def _spawn_running(
    request: AsyncVerifierRequest,
    prepared: _PreparedLaunch,
    popen: PopenFactory,
) -> AsyncVerifierLaunch:
    process = _spawn_process(
        prepared.command,
        prepared.stdout_path,
        prepared.stderr_path,
        popen,
    )
    try:
        return _mark_running_launch(
            request,
            prepared.state_path,
            prepared.command,
            process,
        )
    except POST_SPAWN_ERRORS:
        _cancel_launch(process)
        raise


def _spawn_process(
    command: list[str],
    stdout_path: Path,
    stderr_path: Path,
    popen: PopenFactory,
) -> LaunchedProcess:
    with (
        stdout_path.open("wb") as stdout_handle,
        stderr_path.open("wb") as stderr_handle,
    ):
        return cast(
            "LaunchedProcess",
            popen(  # nosec B603
                command,
                stdin=subprocess.DEVNULL,
                stdout=stdout_handle,
                stderr=stderr_handle,
                close_fds=True,
                start_new_session=True,
            ),
        )


def _mark_running_launch(
    request: AsyncVerifierRequest,
    state_path: Path,
    command: list[str],
    process: LaunchedProcess,
) -> AsyncVerifierLaunch:
    launch = AsyncVerifierLaunch(
        run_id=request.run_id,
        profile=request.profile,
        state_path=state_path,
        process_id=int(process.pid),
        command=tuple(command),
    )
    async_state.mark_async_running(state_path, process_id=launch.process_id)
    return launch


def _launch_error(
    request: AsyncVerifierRequest,
    state_path: Path,
    error: Exception,
) -> AsyncVerifierLaunchError:
    return AsyncVerifierLaunchError(
        f"cannot start verifier {request.run_id}: {error}",
        state_path=state_path,
    )


def _record_launch_error(state_path: Path, error: Exception) -> None:
    with suppress(OSError, async_state.AsyncVerifierStateError):
        async_state.mark_async_terminal(
            state_path,
            status=async_state.JOB_STATUS_ERROR,
            exit_code=None,
            error=str(error),
            phase="spawn",
        )


def _cancel_launch(process: LaunchedProcess) -> None:
    with suppress(OSError):
        process.terminate()
    try:
        process.wait(timeout=PROCESS_STOP_TIMEOUT_SECONDS)
    except (OSError, subprocess.TimeoutExpired):
        with suppress(OSError):
            process.kill()
        with suppress(OSError, subprocess.TimeoutExpired):
            process.wait(timeout=PROCESS_STOP_TIMEOUT_SECONDS)


def _async_child_command(argv: Sequence[str], run_id: str, state_path: Path) -> list[str]:
    verify_args = _child_verify_args(argv, run_id)
    return [
        sys.executable,
        "-m",
        "agent_maintainer.verify.async_child",
        "--state-path",
        str(state_path.resolve()),
        "--",
        *verify_args,
    ]


def _child_verify_args(argv: Sequence[str], run_id: str) -> list[str]:
    args: list[str] = []
    skip_next = False
    for argument in argv:
        if skip_next:
            skip_next = False
            continue
        if argument == ASYNC_FLAG:
            continue
        if argument == RUN_ID_OPTION:
            skip_next = True
            continue
        if argument.startswith(f"{RUN_ID_OPTION}="):
            continue
        args.append(argument)
    return [*args, RUN_ID_OPTION, run_id]
