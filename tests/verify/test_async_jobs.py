"""Tests async verifier job launch helpers."""

from __future__ import annotations

import json
from pathlib import Path

from agent_maintainer.verify.async_jobs import (
    ASYNC_FLAG,
    AsyncVerifierLaunch,
    AsyncVerifierRequest,
    launch_async_verifier,
    render_async_launch,
)

PROCESS_ID = 4321
RENDERED_PROCESS_ID = 123


def test_async_launch_writes_state(tmp_path: Path) -> None:
    """Async launch writes state for verifier child."""
    fake_popen = FakePopen(process_id=PROCESS_ID)

    launch = launch_async_verifier(
        AsyncVerifierRequest(
            argv=("--profile", "fast", ASYNC_FLAG),
            profile="fast",
            run_id="run-1",
            log_dir=tmp_path,
            fingerprint={"profile": "fast"},
        ),
        popen=fake_popen,
    )

    state = json.loads(launch.state_path.read_text(encoding="utf-8"))
    assert launch.process_id == PROCESS_ID
    assert state["run_id"] == "run-1"
    assert state["status"] == "started"
    assert ASYNC_FLAG not in fake_popen.command
    assert fake_popen.command[-5:] == (
        "verify",
        "--profile",
        "fast",
        "--run-id",
        "run-1",
    )


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


class FakePopen:
    """Fake subprocess command."""

    def __init__(self, process_id: int) -> None:
        self.pid = process_id
        self.command: tuple[str, ...] = ()

    def __call__(self, command: list[str], **_kwargs: object) -> FakePopen:
        self.command = tuple(command)
        return self
