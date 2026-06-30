"""Tests bounded command runner behavior."""

from __future__ import annotations

import os
import subprocess  # nosec B404
import sys
import time
from pathlib import Path

import pytest

from agent_maintainer.core import command_run

STDOUT_SIZE = 4_000
STDERR_SIZE = 4_000
OUTPUT_LIMIT = 160
SHORT_TIMEOUT_SECONDS = 1
CHILD_WRITE_DELAY_SECONDS = 2.0
CHILD_WAIT_SECONDS = 2.5
FAKE_PID = 12_345


def test_combined_output_keeps_stderr() -> None:
    """Large stdout does not consume the full output budget before stderr."""

    command = [
        sys.executable,
        "-c",
        (
            "import sys; "
            f"sys.stdout.write('x' * {STDOUT_SIZE}); "
            "sys.stderr.write('important stderr failure')"
        ),
    ]

    exit_code, output = command_run.run_command_bounded(
        command,
        env=os.environ.copy(),
        timeout_seconds=SHORT_TIMEOUT_SECONDS,
        output_limit_chars=OUTPUT_LIMIT,
    )

    assert exit_code == 0
    assert "## stdout" in output
    assert "## stderr" in output
    assert "important stderr failure" in output
    assert "stream truncated" in output


def test_combined_output_preserves_stderr_tail() -> None:
    """Long stderr keeps its tail because failures often end there."""

    command = [
        sys.executable,
        "-c",
        (
            "import sys; "
            "sys.stdout.write('ordinary stdout'); "
            f"sys.stderr.write('start' + 'y' * {STDERR_SIZE} + 'tail-error')"
        ),
    ]

    exit_code, output = command_run.run_command_bounded(
        command,
        env=os.environ.copy(),
        timeout_seconds=SHORT_TIMEOUT_SECONDS,
        output_limit_chars=OUTPUT_LIMIT,
    )

    assert exit_code == 0
    assert "tail-error" in output
    assert "stream truncated" in output


def test_combined_output_tiny_budget(tmp_path: Path) -> None:
    """Tiny per-stream budgets still produce bounded labelled output."""

    stdout_path = tmp_path / "stdout.log"
    stderr_path = tmp_path / "stderr.log"
    stdout_path.write_text("ordinary stdout", encoding="utf-8")
    stderr_path.write_text("stderr tail should be capped", encoding="utf-8")

    output = command_run.combined_output(stdout_path, stderr_path, limit=10)

    assert "## stdout" in output
    assert "## stderr" in output
    assert "stream truncated" in output


def test_process_tree_single_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-POSIX timeout cleanup falls back to terminating one process."""

    fake_process = FakeProcess()
    monkeypatch.setattr(command_run.os, "name", "nt")

    command_run.terminate_process_tree(fake_process)

    assert fake_process.terminated is True
    assert fake_process.killed is False


def test_single_process_timeout_kills() -> None:
    """Single-process cleanup kills when graceful termination times out."""

    fake_process = FakeProcess(timeout_once=True)
    command_run._terminate_single_process(fake_process)
    assert fake_process.terminated is True
    assert fake_process.killed is True


def test_posix_group_missing_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POSIX cleanup tolerates processes that already exited."""

    fake_process = FakeProcess()
    monkeypatch.setattr(command_run.os, "killpg", raise_process_lookup)
    command_run._terminate_posix_group(fake_process)
    assert fake_process.wait_count == 0


def test_posix_group_permission_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POSIX cleanup falls back to single-process termination on permission errors."""

    fake_process = FakeProcess()
    monkeypatch.setattr(command_run.os, "killpg", raise_permission_error)
    command_run._terminate_posix_group(fake_process)

    assert fake_process.terminated is True


def test_posix_process_group_kills_after_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POSIX cleanup sends SIGKILL when SIGTERM does not finish in time."""

    fake_process = FakeProcess(timeout_once=True)
    recorder = SignalRecorder()
    monkeypatch.setattr(command_run.os, "killpg", recorder)

    command_run._terminate_posix_group(fake_process)

    assert recorder.signals == [command_run.signal.SIGTERM, command_run.signal.SIGKILL]


@pytest.mark.skipif(os.name != "posix", reason="process-group cleanup is POSIX-specific")
def test_timeout_kills_process_group(tmp_path: Path) -> None:
    """Timeout cleanup terminates children spawned by the checked command."""

    marker_path = tmp_path / "child-survived.txt"
    child_code = (
        "import pathlib, sys, time; "
        f"time.sleep({CHILD_WRITE_DELAY_SECONDS}); "
        "pathlib.Path(sys.argv[1]).write_text('survived', encoding='utf-8')"
    )
    parent_code = (
        "import subprocess, sys, time; "
        f"subprocess.Popen([sys.executable, '-c', {child_code!r}, sys.argv[1]]); "
        "time.sleep(10)"
    )

    exit_code, output = command_run.run_command_bounded(
        [sys.executable, "-c", parent_code, str(marker_path)],
        env=os.environ.copy(),
        timeout_seconds=SHORT_TIMEOUT_SECONDS,
        output_limit_chars=OUTPUT_LIMIT,
    )
    time.sleep(CHILD_WAIT_SECONDS)

    assert exit_code == command_run.TIMEOUT_EXIT_CODE
    assert "Command timed out" in output
    assert not marker_path.exists()


class FakeProcess:
    """Minimal process double for timeout cleanup tests."""

    pid = FAKE_PID

    def __init__(self, *, timeout_once: bool = False) -> None:
        self.killed = False
        self.terminated = False
        self.timeout_once = timeout_once
        self.wait_count = 0

    def terminate(self) -> None:
        """Record graceful termination."""

        self.terminated = True

    def kill(self) -> None:
        """Record forceful termination."""

        self.killed = True

    def wait(self, timeout: int) -> None:
        """Record wait and optionally raise one timeout."""

        self.wait_count += 1
        if self.timeout_once and self.wait_count == 1:
            raise subprocess.TimeoutExpired(["fake"], timeout)


class SignalRecorder:
    """Record process-group signals."""

    def __init__(self) -> None:
        self.signals: list[int] = []

    def __call__(self, _pid: int, signal_number: int) -> None:
        """Record one process-group signal."""

        self.signals.append(signal_number)


def raise_process_lookup(_pid: int, _signal_number: int) -> None:
    """Raise missing-process error for process-group tests."""

    raise ProcessLookupError


def raise_permission_error(_pid: int, _signal_number: int) -> None:
    """Raise permission error for process-group tests."""

    raise PermissionError
