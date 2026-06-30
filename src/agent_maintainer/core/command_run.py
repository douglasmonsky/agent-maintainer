"""Bounded subprocess execution helpers for verifier checks."""

from __future__ import annotations

import subprocess  # nosec B404
import tempfile
from pathlib import Path

DEFAULT_COMMAND_TIMEOUT_SECONDS = 900
DEFAULT_COMMAND_OUTPUT_LIMIT_CHARS = 1_000_000
TIMEOUT_EXIT_CODE = 124


def run_command_bounded(
    command: list[str],
    *,
    env: dict[str, str],
    timeout_seconds: int | None,
    output_limit_chars: int | None,
) -> tuple[int, str]:
    """Run command using temp files and return bounded combined output."""

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

    with stdout_path.open("wb") as stdout_file, stderr_path.open("wb") as stderr_file:
        return subprocess.run(  # nosec B603
            command,
            stdout=stdout_file,
            stderr=stderr_file,
            env=env,
            check=False,
            timeout=timeout,
        )


def combined_output(stdout_path: Path, stderr_path: Path, limit: int) -> str:
    """Return bounded stdout and stderr text from command temp files."""

    remaining = max(0, limit)
    streams: list[tuple[str, str, bool]] = []
    for label, path in (("stdout", stdout_path), ("stderr", stderr_path)):
        text, truncated = read_bounded_text(path, remaining)
        if text:
            streams.append((label, text, truncated))
        remaining = max(0, remaining - len(text))
        if remaining == 0:
            break
    parts = format_output_streams(streams)
    if remaining == 0:
        parts.append(f"... command output truncated at {limit} characters.")
    return "\n".join(parts)


def format_output_streams(streams: list[tuple[str, str, bool]]) -> list[str]:
    """Return command output parts, preserving simple stdout-only output."""

    if len(streams) == 1:
        _label, text, truncated = streams[0]
        suffix = "\n... stream truncated." if truncated else ""
        return [f"{text.rstrip()}{suffix}"]
    return [format_output_part(label, text, truncated) for label, text, truncated in streams]


def format_output_part(label: str, text: str, truncated: bool) -> str:
    """Return one labelled output stream for a command log."""

    suffix = "\n... stream truncated." if truncated else ""
    return f"## {label}\n{text.rstrip()}{suffix}"


def read_bounded_text(path: Path, limit: int) -> tuple[str, bool]:
    """Read at most limit characters from a command output file."""

    if limit <= 0 or not path.exists():
        return "", path.exists() and path.stat().st_size > 0
    with path.open("rb") as handle:
        payload = handle.read(limit + 1)
    truncated = len(payload) > limit
    if truncated:
        payload = payload[:limit]
    return payload.decode("utf-8", errors="replace"), truncated
