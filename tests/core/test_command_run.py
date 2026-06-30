"""Tests bounded command runner behavior."""

from __future__ import annotations

import os
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
