"""Bounded subprocess execution for MCP-backed local tools."""

from __future__ import annotations

import os
import signal
import subprocess  # nosec B404
from collections import deque
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import IO

DEFAULT_HARD_OUTPUT_LIMIT_BYTES = 1_048_576
STREAM_CHUNK_BYTES = 65_536
TAIL_ENCODING_MULTIPLIER = 4


@dataclass(frozen=True)
class BoundedStreamCapture:
    """Bounded tail and accounting for one child output stream."""

    tail: bytes
    total_bytes: int
    truncated: bool
    limit_exceeded: bool

    def text(self) -> str:
        """Decode the retained tail without propagating encoding failures."""

        return self.tail.decode("utf-8", errors="replace")


@dataclass(frozen=True)
class BoundedProcessCapture:
    """Terminal state and bounded output for one child process."""

    returncode: int
    stdout: BoundedStreamCapture
    stderr: BoundedStreamCapture
    timed_out: bool = False


@dataclass(frozen=True)
class BoundedProcessOptions:
    """Resource ceilings for one MCP child process."""

    timeout_seconds: int
    output_limit_chars: int
    hard_output_limit_bytes: int = DEFAULT_HARD_OUTPUT_LIMIT_BYTES


def run_bounded_process(
    command: tuple[str, ...],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    options: BoundedProcessOptions,
) -> BoundedProcessCapture:
    """Run a child while bounding retained and total output per stream."""

    retain_bytes = min(
        options.hard_output_limit_bytes,
        max(options.output_limit_chars * TAIL_ENCODING_MULTIPLIER, STREAM_CHUNK_BYTES),
    )
    with _start_process(command, cwd=cwd, environment=environment) as process:
        stdout, stderr, timed_out = _capture_process(
            process,
            timeout_seconds=options.timeout_seconds,
            retain_bytes=retain_bytes,
            hard_output_limit_bytes=options.hard_output_limit_bytes,
        )
        returncode = process.returncode
    return BoundedProcessCapture(
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        timed_out=timed_out,
    )


def _start_process(
    command: tuple[str, ...],
    *,
    cwd: Path,
    environment: Mapping[str, str],
) -> subprocess.Popen[bytes]:
    """Start one non-interactive child in its own process group."""

    return subprocess.Popen(  # nosec B603
        command,
        cwd=cwd,
        env=dict(environment),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=os.name == "posix",
    )


def _capture_process(
    process: subprocess.Popen[bytes],
    *,
    timeout_seconds: int,
    retain_bytes: int,
    hard_output_limit_bytes: int,
) -> tuple[BoundedStreamCapture, BoundedStreamCapture, bool]:
    """Drain both child streams concurrently through bounded collectors."""

    stdout_stream = _required_stream(process.stdout, label="stdout")
    stderr_stream = _required_stream(process.stderr, label="stderr")
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="mcp-output") as executor:
        stdout_future = executor.submit(
            _read_stream,
            stdout_stream,
            process,
            retain_bytes=retain_bytes,
            hard_output_limit_bytes=hard_output_limit_bytes,
        )
        stderr_future = executor.submit(
            _read_stream,
            stderr_stream,
            process,
            retain_bytes=retain_bytes,
            hard_output_limit_bytes=hard_output_limit_bytes,
        )
        timed_out = _wait_for_process(process, timeout_seconds=timeout_seconds)
        return stdout_future.result(), stderr_future.result(), timed_out


def _read_stream(
    stream: IO[bytes],
    process: subprocess.Popen[bytes],
    *,
    retain_bytes: int,
    hard_output_limit_bytes: int,
) -> BoundedStreamCapture:
    """Drain one stream while retaining only its tail."""

    retained: deque[int] = deque(maxlen=retain_bytes)
    total_bytes = 0
    limit_exceeded = False
    try:
        while chunk := stream.read(STREAM_CHUNK_BYTES):
            total_bytes += len(chunk)
            retained.extend(chunk)
            if total_bytes > hard_output_limit_bytes:
                limit_exceeded = True
                _kill_process_group(process)
                break
    except OSError:
        _kill_process_group(process)
    return BoundedStreamCapture(
        tail=bytes(retained),
        total_bytes=total_bytes,
        truncated=total_bytes > len(retained),
        limit_exceeded=limit_exceeded,
    )


def _wait_for_process(process: subprocess.Popen[bytes], *, timeout_seconds: int) -> bool:
    """Wait for a child, killing its process group on timeout."""

    try:
        process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        _kill_process_group(process)
        process.wait()
        return True
    return False


def _kill_process_group(process: subprocess.Popen[bytes]) -> None:
    """Kill a still-running child and its descendants when supported."""

    if process.poll() is not None:
        return
    if os.name == "posix":
        with suppress(OSError):
            os.killpg(process.pid, signal.SIGKILL)
        return
    with suppress(OSError):
        process.kill()


def _required_stream(stream: IO[bytes] | None, *, label: str) -> IO[bytes]:
    """Return a configured process pipe or fail before waiting."""

    if stream is None:
        raise RuntimeError(f"MCP child {label} pipe is unavailable")
    return stream
