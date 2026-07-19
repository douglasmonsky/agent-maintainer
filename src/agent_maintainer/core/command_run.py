"""Bounded subprocess execution helpers for verifier checks."""

from __future__ import annotations

import os
import signal
import subprocess  # nosec B404
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

DEFAULT_COMMAND_TIMEOUT_SECONDS = 900
DEFAULT_COMMAND_OUTPUT_LIMIT_CHARS = 1_000_000
TIMEOUT_EXIT_CODE = 124
TERMINATE_GRACE_SECONDS = 5
TRUNCATION_MARKER_ALLOWANCE = 40


class CommandRunError(RuntimeError):
    """Bounded command execution failed without exposing command output."""


@dataclass(frozen=True)
class CommandFileRun:
    """Inputs for one shell-free command whose streams go to files."""

    command: list[str]
    stdout_path: Path
    stderr_path: Path
    env: dict[str, str]
    timeout: int
    cwd: Path | None = None


class TerminableProcess(Protocol):
    """Process operations required for timeout cleanup."""

    pid: int

    def terminate(self) -> None:
        """Terminate the process gracefully."""

    def kill(self) -> None:
        """Kill the process forcefully."""

    def wait(self, timeout: int) -> int | None:
        """Wait for the process to exit."""


def run_command_bounded(
    command: list[str],
    *,
    env: dict[str, str],
    timeout_seconds: int | None,
    output_limit_chars: int | None,
) -> tuple[int, str]:
    """Run command with temp-file output capture and bounded combined output."""

    limit = output_limit_chars or DEFAULT_COMMAND_OUTPUT_LIMIT_CHARS
    timeout = timeout_seconds or DEFAULT_COMMAND_TIMEOUT_SECONDS
    with tempfile.TemporaryDirectory(prefix="agent-maintainer-output-") as temp_dir:
        stdout_path = Path(temp_dir) / "stdout.log"
        stderr_path = Path(temp_dir) / "stderr.log"
        try:
            result = run_command_to_files(command, stdout_path, stderr_path, env, timeout)
        except subprocess.TimeoutExpired:
            output = combined_output(stdout_path, stderr_path, limit)
            timeout_note = f"Command timed out after {timeout} second(s)."
            return (
                TIMEOUT_EXIT_CODE,
                "\n".join(part for part in (output, timeout_note) if part),
            )
        return result.returncode, combined_output(stdout_path, stderr_path, limit)


def run_command_to_files(
    command: list[str],
    stdout_path: Path,
    stderr_path: Path,
    env: dict[str, str],
    timeout: int,
) -> subprocess.CompletedProcess[bytes]:
    """Run command with stdout and stderr redirected to files."""

    return _run_command_to_files(
        CommandFileRun(command, stdout_path, stderr_path, env, timeout),
    )


def _run_command_to_files(request: CommandFileRun) -> subprocess.CompletedProcess[bytes]:
    """Execute a validated file-output request without a shell."""

    with (
        request.stdout_path.open("wb") as stdout_file,
        request.stderr_path.open("wb") as stderr_file,
        subprocess.Popen(  # nosec B603
            request.command,
            stdout=stdout_file,
            stderr=stderr_file,
            cwd=request.cwd,
            env=request.env,
            start_new_session=os.name == "posix",
        ) as process,
    ):
        try:
            process.wait(timeout=request.timeout)
        except subprocess.TimeoutExpired:
            terminate_process_tree(process)
            raise
        except BaseException:
            if process.poll() is None:
                terminate_process_tree(process)
            raise
        return subprocess.CompletedProcess(request.command, process.returncode)


def run_command_bytes_bounded(
    command: list[str],
    *,
    cwd: Path,
    timeout_seconds: int,
    output_limit_bytes: int,
) -> bytes:
    """Run one shell-free command and return size-bounded stdout bytes."""

    with tempfile.TemporaryDirectory(prefix="agent-maintainer-bytes-") as temp_dir:
        stdout_path = Path(temp_dir) / "stdout.bin"
        stderr_path = Path(temp_dir) / "stderr.bin"
        try:
            result = _run_command_to_files(
                CommandFileRun(
                    command,
                    stdout_path,
                    stderr_path,
                    os.environ.copy(),
                    timeout_seconds,
                    cwd,
                ),
            )
        except subprocess.TimeoutExpired as exc:
            raise CommandRunError("command exceeded the time limit") from exc
        if result.returncode:
            raise CommandRunError("command returned a nonzero status")
        return _read_bounded_bytes(stdout_path, output_limit_bytes)


def _read_bounded_bytes(path: Path, limit: int) -> bytes:
    """Read a regular command-output file only after checking its size."""

    try:
        size = path.stat().st_size
    except OSError as exc:
        raise CommandRunError("command output could not be inspected") from exc
    if size > limit:
        raise CommandRunError("command output exceeded the size limit")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise CommandRunError("command output could not be read") from exc


def terminate_process_tree(process: TerminableProcess) -> None:
    """Terminate a process and, on POSIX, its child process group."""

    if os.name == "posix":
        _terminate_posix_group(process)
        return
    _terminate_single_process(process)


def combined_output(stdout_path: Path, stderr_path: Path, limit: int) -> str:
    """Return bounded output while preserving stdout and stderr visibility."""

    streams = [
        ("stdout", stdout_path),
        ("stderr", stderr_path),
    ]
    present = [(label, path) for label, path in streams if _file_has_content(path)]
    if not present:
        return ""
    if len(present) == 1:
        label, path = present[0]
        text, truncated = read_bounded_text(path, limit, preserve_tail=False)
        return "\n".join(format_output_streams([(label, text, truncated)]))
    budget = max(1, limit // len(present))
    stream_outputs = [
        (label, *read_bounded_text(path, budget, preserve_tail=True)) for label, path in present
    ]
    return "\n".join(format_output_streams(stream_outputs))


def format_output_streams(streams: list[tuple[str, str, bool]]) -> list[str]:
    """Return output parts, preserving simple stdout-only output."""

    if len(streams) == 1:
        _label, text, truncated = streams[0]
        suffix = "\n... stream truncated." if truncated else ""
        return [f"{text.rstrip()}{suffix}"]
    return [format_output_part(label, text, truncated) for label, text, truncated in streams]


def format_output_part(label: str, text: str, truncated: bool) -> str:
    """Return one labelled output stream command log."""

    suffix = "\n... stream truncated." if truncated else ""
    return f"## {label}\n{text.rstrip()}{suffix}"


def read_bounded_text(
    path: Path,
    limit: int,
    *,
    preserve_tail: bool,
) -> tuple[str, bool]:
    """Return bounded decoded text from an output file."""

    if limit <= 0 or not path.exists():
        return "", path.exists() and path.stat().st_size > 0
    if preserve_tail:
        return _read_head_tail(path, limit)
    with path.open("rb") as handle:
        payload = handle.read(limit + 1)
    truncated = len(payload) > limit
    if truncated:
        payload = payload[:limit]
    return payload.decode("utf-8", errors="replace"), truncated


def _read_head_tail(path: Path, limit: int) -> tuple[str, bool]:
    """Return head and tail slices so stderr endings survive output caps."""

    size = path.stat().st_size
    if size <= limit:
        return path.read_text(encoding="utf-8", errors="replace"), False
    if limit <= TRUNCATION_MARKER_ALLOWANCE:
        with path.open("rb") as handle:
            payload = handle.read(limit)
        return payload.decode("utf-8", errors="replace"), True
    head_limit = max(1, (limit - TRUNCATION_MARKER_ALLOWANCE) // 2)
    tail_limit = max(1, limit - TRUNCATION_MARKER_ALLOWANCE - head_limit)
    with path.open("rb") as handle:
        head = handle.read(head_limit)
        handle.seek(-tail_limit, os.SEEK_END)
        tail = handle.read(tail_limit)
    omitted = max(0, size - head_limit - tail_limit)
    marker = f"\n... stream truncated; omitted {omitted} byte(s) ...\n"
    payload = head + marker.encode("utf-8") + tail
    return payload.decode("utf-8", errors="replace"), True


def _terminate_posix_group(process: TerminableProcess) -> None:
    """Terminate a POSIX process group with a kill fallback."""

    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except PermissionError:
        _terminate_single_process(process)
        return
    try:
        process.wait(timeout=TERMINATE_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=TERMINATE_GRACE_SECONDS)


def _terminate_single_process(process: TerminableProcess) -> None:
    """Terminate a single process when process groups are unavailable."""

    process.terminate()
    try:
        process.wait(timeout=TERMINATE_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=TERMINATE_GRACE_SECONDS)


def _file_has_content(path: Path) -> bool:
    """Return whether output file exists and has content."""

    return path.exists() and path.stat().st_size > 0
