"""Read bounded line-oriented Git output for attention signals."""

from __future__ import annotations

import subprocess  # nosec B404
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from threading import Event, Timer

DEFAULT_GIT_OUTPUT_BYTES = 1_048_576
DEFAULT_GIT_OUTPUT_LINES = 10_000
DEFAULT_GIT_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True)
class BoundedCommandLines:
    """Bounded command lines and terminal collection state."""

    lines: tuple[str, ...]
    truncated: bool = False
    timed_out: bool = False


def git_lines(
    repo_root: Path,
    args: tuple[str, ...],
    *,
    line_limit: int = DEFAULT_GIT_OUTPUT_LINES,
    byte_limit: int = DEFAULT_GIT_OUTPUT_BYTES,
    timeout_seconds: float = DEFAULT_GIT_TIMEOUT_SECONDS,
) -> BoundedCommandLines:
    """Return bounded output from one fixed Git command."""

    return command_lines(
        ("git", *args),
        cwd=repo_root,
        line_limit=line_limit,
        byte_limit=byte_limit,
        timeout_seconds=timeout_seconds,
    )


def command_lines(
    command: tuple[str, ...],
    *,
    cwd: Path,
    line_limit: int,
    byte_limit: int,
    timeout_seconds: float,
) -> BoundedCommandLines:
    """Stream command stdout within count, byte, and time ceilings."""

    try:
        process = _start_process(command, cwd=cwd)
    except OSError:
        return BoundedCommandLines(())
    timeout_reached = Event()
    timer = Timer(timeout_seconds, _expire_process, args=(process, timeout_reached))
    timer.daemon = True
    timer.start()
    result = _consume_stdout(process, line_limit=line_limit, byte_limit=byte_limit)
    _wait_process(process)
    _finish_process(process, timer)
    if timeout_reached.is_set():
        return BoundedCommandLines((), truncated=True, timed_out=True)
    if process.returncode != 0 and not result.truncated:
        return BoundedCommandLines(())
    return result


def _start_process(
    command: tuple[str, ...],
    *,
    cwd: Path,
) -> subprocess.Popen[str]:
    """Start one line-buffered command with no inherited output streams."""

    return subprocess.Popen(  # nosec B603
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _consume_stdout(
    process: subprocess.Popen[str],
    *,
    line_limit: int,
    byte_limit: int,
) -> BoundedCommandLines:
    """Consume a process pipe until EOF or the first configured ceiling."""

    if process.stdout is None:
        return BoundedCommandLines(())
    try:
        return _read_stdout_lines(process, line_limit=line_limit, byte_limit=byte_limit)
    except OSError:
        return BoundedCommandLines(())


def _read_stdout_lines(
    process: subprocess.Popen[str],
    *,
    line_limit: int,
    byte_limit: int,
) -> BoundedCommandLines:
    """Read available child lines until EOF or the first ceiling."""

    if process.stdout is None:
        return BoundedCommandLines(())
    lines: list[str] = []
    consumed_bytes = 0
    for raw_line in process.stdout:
        consumed_bytes += len(raw_line.encode("utf-8"))
        if len(lines) >= line_limit or consumed_bytes > byte_limit:
            _kill_process(process)
            return BoundedCommandLines(tuple(lines), truncated=True)
        line = raw_line.strip()
        if line:
            lines.append(line)
    return BoundedCommandLines(tuple(lines))


def _wait_process(process: subprocess.Popen[str]) -> None:
    """Reap a child after normal completion, timeout, or cap termination."""

    with suppress(OSError):
        process.wait()


def _finish_process(process: subprocess.Popen[str], timer: Timer) -> None:
    """Cancel the watchdog and close remaining child resources."""

    timer.cancel()
    _close_stdout(process)
    _kill_process(process)


def _expire_process(process: subprocess.Popen[str], reached: Event) -> None:
    """Record timeout and stop the child process."""

    reached.set()
    _kill_process(process)


def _kill_process(process: subprocess.Popen[str]) -> None:
    """Kill a still-running child without masking its caller's result."""

    if process.poll() is None:
        with suppress(OSError):
            process.kill()


def _close_stdout(process: subprocess.Popen[str]) -> None:
    """Close the parent copy of a child stdout pipe."""

    if process.stdout is not None:
        with suppress(OSError):
            process.stdout.close()
