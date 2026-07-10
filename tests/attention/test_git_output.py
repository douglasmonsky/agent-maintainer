"""Tests bounded attention Git output collection."""

from __future__ import annotations

import sys
import time
from pathlib import Path

from agent_maintainer.attention import git_output

MAX_TIMEOUT_TEST_SECONDS = 2


def test_command_lines_stops_at_line_limit(tmp_path: Path) -> None:
    """A rapid producer cannot make the collector retain unlimited lines."""

    result = git_output.command_lines(
        (sys.executable, "-c", "print('item\\n' * 100)"),
        cwd=tmp_path,
        line_limit=3,
        byte_limit=1_000,
        timeout_seconds=2,
    )

    assert result.lines == ("item", "item", "item")
    assert result.truncated is True
    assert result.timed_out is False


def test_command_lines_stops_at_byte_limit(tmp_path: Path) -> None:
    """One long line cannot bypass the aggregate byte ceiling."""

    result = git_output.command_lines(
        (sys.executable, "-c", "print('x' * 100)"),
        cwd=tmp_path,
        line_limit=100,
        byte_limit=10,
        timeout_seconds=2,
    )

    assert result.lines == ()
    assert result.truncated is True


def test_command_lines_kills_timeout(tmp_path: Path) -> None:
    """A silent child is killed when the collection deadline expires."""

    started = time.monotonic()
    result = git_output.command_lines(
        (sys.executable, "-c", "import time; time.sleep(5)"),
        cwd=tmp_path,
        line_limit=100,
        byte_limit=1_000,
        timeout_seconds=0.05,
    )

    assert result.lines == ()
    assert result.timed_out is True
    assert time.monotonic() - started < MAX_TIMEOUT_TEST_SECONDS
