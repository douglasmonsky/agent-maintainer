"""Tests the owned detached-verifier child entrypoint."""

from __future__ import annotations

import os
import signal
import time
from pathlib import Path

import pytest

from agent_maintainer.verify import async_child, async_state


@pytest.mark.parametrize(
    ("exit_code", "expected_status"),
    (
        (0, async_state.JOB_STATUS_PASSED),
        (1, async_state.JOB_STATUS_FAILED),
    ),
)
def test_async_child_persists_quality_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    exit_code: int,
    expected_status: str,
) -> None:
    """Normal verifier exit codes become pass/fail job states."""

    state_path = write_running_state(tmp_path)
    seen: list[list[str]] = []
    monkeypatch.setattr(
        async_child.quiet,
        "main",
        lambda argv: seen.append(argv) or exit_code,
    )

    status = async_child.main(
        ["--state-path", str(state_path), "--", "--profile", "fast", "--run-id", "run-1"],
    )

    state = async_state.read_async_state(state_path)
    assert status == exit_code
    assert seen == [["--profile", "fast", "--run-id", "run-1"]]
    assert state is not None
    assert state.status == expected_status
    assert state.exit_code == exit_code


def test_async_child_persists_infrastructure_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Unexpected child exceptions remain distinct from failed checks."""

    state_path = write_running_state(tmp_path)
    error = RuntimeError("runner crashed")
    async_child.record_unhandled_exception(
        state_path,
        RuntimeError,
        error,
        error.__traceback__,
    )

    state = async_state.read_async_state(state_path)
    assert state is not None
    assert state.status == async_state.JOB_STATUS_ERROR
    assert state.exit_code == async_child.UNHANDLED_EXCEPTION_STATUS
    assert state.error == "RuntimeError: runner crashed"
    assert "RuntimeError: runner crashed" in capsys.readouterr().err


def test_async_child_persists_signal_cancellation(tmp_path: Path) -> None:
    """External cancellation is durable before the child exits."""

    state_path = write_running_state(tmp_path)

    with pytest.raises(SystemExit) as raised:
        async_child.cancel_for_signal(state_path, signal.SIGTERM)

    state = async_state.read_async_state(state_path)
    expected_exit = async_child.SIGNAL_EXIT_OFFSET + signal.SIGTERM
    assert raised.value.code == expected_exit
    assert state is not None
    assert state.status == async_state.JOB_STATUS_CANCELLED
    assert state.exit_code == expected_exit
    assert "SIGTERM" in state.error


def write_running_state(tmp_path: Path) -> Path:
    """Write a state owned by the current test process."""

    jobs_dir = tmp_path / "jobs"
    state_path = jobs_dir / "run-1.json"
    now = time.time()
    async_state.write_async_state(
        state_path,
        async_state.AsyncVerifierState(
            run_id="run-1",
            profile="fast",
            status=async_state.JOB_STATUS_RUNNING,
            process_id=os.getpid(),
            command=("python", "-m", "agent_maintainer.verify.async_child"),
            fingerprint={"profile": "fast"},
            stdout_path=str(jobs_dir / "run-1.stdout.log"),
            stderr_path=str(jobs_dir / "run-1.stderr.log"),
            started_at=now,
            updated_at=now,
            phase="verify",
        ),
    )
    return state_path
