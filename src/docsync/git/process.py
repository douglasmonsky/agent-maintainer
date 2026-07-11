"""Bounded subprocess execution for DocSync Git reads."""

from __future__ import annotations

import subprocess  # nosec B404
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import IO

DEFAULT_GIT_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_GIT_STDOUT_BYTES = 16_777_216
DEFAULT_MAX_GIT_STDERR_BYTES = 65_536
STREAM_CHUNK_BYTES = 65_536


class GitProcessError(ValueError):
    """Raised when bounded Git process execution fails."""


@dataclass(frozen=True)
class GitProcessResult:
    """Bounded decoded output and status from one Git command."""

    returncode: int
    stdout: str
    stderr: str


def run_git(
    repo_root: Path,
    args: tuple[str, ...],
    *,
    timeout_seconds: float = DEFAULT_GIT_TIMEOUT_SECONDS,
    max_stdout_bytes: int = DEFAULT_MAX_GIT_STDOUT_BYTES,
    max_stderr_bytes: int = DEFAULT_MAX_GIT_STDERR_BYTES,
) -> GitProcessResult:
    """Run Git with concurrent bounded output capture and a hard deadline."""

    with _start_git(repo_root, args) as process:
        stdout, stderr = _capture_process(
            process,
            timeout_seconds=timeout_seconds,
            max_stdout_bytes=max_stdout_bytes,
            max_stderr_bytes=max_stderr_bytes,
        )
        returncode = process.returncode
    return GitProcessResult(
        returncode=returncode,
        stdout=_decode_output(stdout),
        stderr=_decode_output(stderr),
    )


def _start_git(repo_root: Path, args: tuple[str, ...]) -> subprocess.Popen[bytes]:
    try:
        return subprocess.Popen(  # nosec B603, B607
            ("git", *args),
            cwd=repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        raise GitProcessError("Cannot start Git command") from exc


def _capture_process(
    process: subprocess.Popen[bytes],
    *,
    timeout_seconds: float,
    max_stdout_bytes: int,
    max_stderr_bytes: int,
) -> tuple[bytes, bytes]:
    stdout_stream = _require_stream(process.stdout, label="stdout")
    stderr_stream = _require_stream(process.stderr, label="stderr")
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="docsync-git") as executor:
        stdout_future = executor.submit(
            _read_bounded_stream,
            stdout_stream,
            process,
            label="stdout",
            max_bytes=max_stdout_bytes,
        )
        stderr_future = executor.submit(
            _read_bounded_stream,
            stderr_stream,
            process,
            label="stderr",
            max_bytes=max_stderr_bytes,
        )
        _wait_for_process(process, timeout_seconds=timeout_seconds)
        return stdout_future.result(), stderr_future.result()


def _read_bounded_stream(
    stream: IO[bytes],
    process: subprocess.Popen[bytes],
    *,
    label: str,
    max_bytes: int,
) -> bytes:
    captured = bytearray()
    try:
        while chunk := stream.read(_next_read_size(len(captured), max_bytes)):
            captured.extend(chunk)
            if len(captured) > max_bytes:
                _kill_process(process)
                raise GitProcessError(f"Git {label} exceeds the {max_bytes}-byte limit")
    except OSError as exc:
        _kill_process(process)
        raise GitProcessError(f"Cannot read Git {label}") from exc
    return bytes(captured)


def _next_read_size(captured_bytes: int, max_bytes: int) -> int:
    return min(STREAM_CHUNK_BYTES, max_bytes - captured_bytes + 1)


def _wait_for_process(process: subprocess.Popen[bytes], *, timeout_seconds: float) -> None:
    try:
        process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        _kill_process(process)
        process.wait()
        timeout_label = str(timeout_seconds)
        raise GitProcessError(f"Git command timed out after {timeout_label} seconds") from exc


def _kill_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        process.kill()
    except OSError:
        return


def _require_stream(stream: IO[bytes] | None, *, label: str) -> IO[bytes]:
    if stream is None:
        raise GitProcessError(f"Git {label} pipe is unavailable")
    return stream


def _decode_output(output: bytes) -> str:
    return output.decode("utf-8", errors="replace")
