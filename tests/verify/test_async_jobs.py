"""Tests async verifier job launch and durable lifecycle state."""

from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

import pytest

from agent_maintainer.verify import async_state
from agent_maintainer.verify.async_jobs import (
    ASYNC_FLAG,
    JOBS_DIR_NAME,
    AsyncVerifierLaunch,
    AsyncVerifierLaunchError,
    AsyncVerifierRequest,
    launch_async_verifier,
    render_async_launch,
)

PROCESS_ID = 4321
RENDERED_PROCESS_ID = 123


def test_async_launch_owns_streams_and_writes_running_state(tmp_path: Path) -> None:
    """Async launch persists before spawn and owns every inherited stream."""

    request = async_request(tmp_path)
    fake_popen = FakePopen(process_id=PROCESS_ID, state_path=job_state_path(request))

    launch = launch_async_verifier(request, popen=fake_popen)

    state = async_state.read_async_state(launch.state_path)
    assert state is not None
    assert fake_popen.state_at_spawn == async_state.JOB_STATUS_STARTING
    assert state.status == async_state.JOB_STATUS_RUNNING
    assert state.process_id == PROCESS_ID
    assert state.updated_at >= state.started_at
    assert launch.process_id == PROCESS_ID
    assert fake_popen.kwargs["stdin"] == subprocess.DEVNULL
    assert fake_popen.kwargs["close_fds"] is True
    assert fake_popen.kwargs["start_new_session"] is True
    stdout_handle = fake_popen.kwargs["stdout"]
    stderr_handle = fake_popen.kwargs["stderr"]
    assert isinstance(stdout_handle, io.IOBase)
    assert isinstance(stderr_handle, io.IOBase)
    assert stdout_handle.closed is True
    assert stderr_handle.closed is True
    assert ASYNC_FLAG not in fake_popen.command
    assert fake_popen.command.count("--run-id") == 1
    assert fake_popen.command[-4:] == ("--profile", "fast", "--run-id", "run-1")


def test_async_spawn_failure_is_durable_infrastructure_error(tmp_path: Path) -> None:
    """Spawn failure records an error instead of looking like a quality failure."""

    request = async_request(tmp_path)

    with pytest.raises(AsyncVerifierLaunchError, match="cannot start verifier run-1"):
        launch_async_verifier(request, popen=FailingPopen())

    state = async_state.read_async_state(job_state_path(request))
    assert state is not None
    assert state.status == async_state.JOB_STATUS_ERROR
    assert state.phase == "spawn"
    assert "spawn unavailable" in state.error
    assert state.exit_code is None


def test_async_launch_renders_wait_command(tmp_path: Path) -> None:
    """Async launch tells agents which wait command to run."""

    launch = AsyncVerifierLaunch(
        run_id="run-2",
        profile="full",
        state_path=tmp_path / "jobs" / "run-2.json",
        process_id=RENDERED_PROCESS_ID,
        command=("python", "-m", "agent_maintainer", "verify"),
    )

    text = render_async_launch(launch)

    assert "Result: PENDING\nProfile: full\nRun ID: run-2" in text
    assert "python -m agent_maintainer wait verifier run-2" in text


def async_request(tmp_path: Path) -> AsyncVerifierRequest:
    """Return one deterministic async verifier request."""

    return AsyncVerifierRequest(
        argv=("--profile", "fast", ASYNC_FLAG, "--run-id", "parent-run"),
        profile="fast",
        run_id="run-1",
        log_dir=tmp_path,
        fingerprint={"profile": "fast"},
    )


def job_state_path(request: AsyncVerifierRequest) -> Path:
    """Return durable state path for a request."""

    return request.log_dir / JOBS_DIR_NAME / f"{request.run_id}.json"


class FakePopen:
    """Process double recording detached launch arguments."""

    def __init__(self, process_id: int, state_path: Path) -> None:
        self.pid = process_id
        self.state_path = state_path
        self.command: tuple[str, ...] = ()
        self.kwargs: dict[str, object] = {}
        self.state_at_spawn = ""

    def __call__(self, command: list[str], **kwargs: object) -> FakePopen:
        self.command = tuple(command)
        self.kwargs = kwargs
        payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.state_at_spawn = str(payload["status"])
        return self

    def terminate(self) -> None:
        """Satisfy launch-cleanup protocol."""

    def kill(self) -> None:
        """Satisfy launch-cleanup protocol."""

    def wait(self, timeout: float | None = None) -> int:
        """Satisfy launch-cleanup protocol."""

        return 0


class FailingPopen:
    """Process factory that cannot create a child."""

    def __call__(self, _command: list[str], **_kwargs: object) -> object:
        raise OSError("spawn unavailable")
