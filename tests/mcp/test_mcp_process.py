"""Tests bounded process execution for MCP-backed tools."""

from __future__ import annotations

import sys
import time
from pathlib import Path

from agent_maintainer.mcp import process as mcp_process

HARD_OUTPUT_LIMIT = 4_096
RETAINED_OUTPUT_CHARS = 64
MAX_TEST_RUNTIME_SECONDS = 2
DUAL_STREAM_BYTES = 1_024


def test_rapid_output_is_killed_at_hard_limit(tmp_path: Path) -> None:
    """A fast producer cannot grow parent memory beyond the stream ceiling."""

    started = time.monotonic()
    result = mcp_process.run_bounded_process(
        (
            sys.executable,
            "-c",
            "import os\nwhile True: os.write(1, b'x' * 4096)",
        ),
        cwd=tmp_path,
        environment={},
        options=mcp_process.BoundedProcessOptions(
            timeout_seconds=5,
            output_limit_chars=RETAINED_OUTPUT_CHARS,
            hard_output_limit_bytes=HARD_OUTPUT_LIMIT,
        ),
    )

    assert result.returncode != 0
    assert result.stdout.limit_exceeded is True
    assert result.stdout.total_bytes <= HARD_OUTPUT_LIMIT + mcp_process.STREAM_CHUNK_BYTES
    assert len(result.stdout.tail) <= HARD_OUTPUT_LIMIT
    assert time.monotonic() - started < MAX_TEST_RUNTIME_SECONDS


def test_silent_child_is_killed_on_timeout(tmp_path: Path) -> None:
    """A non-producing child is terminated and reaped at its deadline."""

    started = time.monotonic()
    result = mcp_process.run_bounded_process(
        (sys.executable, "-c", "import time; time.sleep(5)"),
        cwd=tmp_path,
        environment={},
        options=mcp_process.BoundedProcessOptions(
            timeout_seconds=0,
            output_limit_chars=RETAINED_OUTPUT_CHARS,
            hard_output_limit_bytes=HARD_OUTPUT_LIMIT,
        ),
    )

    assert result.returncode != 0
    assert result.timed_out is True
    assert time.monotonic() - started < MAX_TEST_RUNTIME_SECONDS


def test_stdout_and_stderr_are_drained_concurrently(tmp_path: Path) -> None:
    """Large writes to both pipes complete without a pipe deadlock."""

    result = mcp_process.run_bounded_process(
        (
            sys.executable,
            "-c",
            (
                "import os\n"
                f"os.write(1, b'o' * {DUAL_STREAM_BYTES})\n"
                f"os.write(2, b'e' * {DUAL_STREAM_BYTES})"
            ),
        ),
        cwd=tmp_path,
        environment={},
        options=mcp_process.BoundedProcessOptions(
            timeout_seconds=5,
            output_limit_chars=RETAINED_OUTPUT_CHARS,
            hard_output_limit_bytes=HARD_OUTPUT_LIMIT,
        ),
    )

    assert result.returncode == 0
    assert result.stdout.total_bytes == DUAL_STREAM_BYTES
    assert result.stderr.total_bytes == DUAL_STREAM_BYTES
