"""Git helpers for bounded diff context."""

from __future__ import annotations

import subprocess  # nosec B404
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DIFF_CONTEXT_LINES = 3
DEFAULT_DIFF_PATH_LIMIT = 80


@dataclass(frozen=True)
class DiffRequest:
    """Requested diff context."""

    repo: Path
    base_ref: str = "HEAD"
    staged: bool = False
    summary: bool = False
    name_only: bool = False
    path: str | None = None
    limit: int = DEFAULT_DIFF_PATH_LIMIT
    hunks: int | None = None
    budget: int = 12_000


@dataclass(frozen=True)
class FileChange:
    """One changed file summary."""

    path: str
    additions: int
    deletions: int

    @property
    def changed_lines(self) -> int:
        """Return changed line count."""

        return self.additions + self.deletions


def changed_paths(request: DiffRequest) -> tuple[str, ...]:
    """Return changed paths."""

    output = run_git([*diff_args(request, "--name-only"), "--"])
    return tuple(line for line in output.splitlines() if line)


def file_changes(request: DiffRequest) -> tuple[FileChange, ...]:
    """Return changed line counts by file."""

    output = run_git([*diff_args(request, "--numstat"), "--"])
    return tuple(parse_numstat_line(line) for line in output.splitlines() if line)


def name_status_lines(request: DiffRequest) -> tuple[str, ...]:
    """Return Git name-status output lines."""

    return tuple(run_git([*diff_args(request, "--name-status"), "--"]).splitlines())


def parse_numstat_line(line: str) -> FileChange:
    """Parse one git numstat line."""

    added, deleted, path = line.split("\t", maxsplit=2)
    return FileChange(path=path, additions=parse_count(added), deletions=parse_count(deleted))


def parse_count(value: str) -> int:
    """Parse numstat count with binary marker support."""

    return int(value) if value.isdecimal() else 0


def git_diff(request: DiffRequest, *, path: str | None = None) -> str:
    """Return git patch output."""

    args = diff_args(request, f"--unified={DEFAULT_DIFF_CONTEXT_LINES}")
    args.append("--")
    if path:
        args.append(path)
    return run_git(args)


def diff_args(request: DiffRequest, mode: str) -> list[str]:
    """Return Git diff command arguments."""

    args = ["git", "-C", str(request.repo), "diff", mode]
    if request.staged:
        args.append("--cached")
    else:
        args.append(validated_git_revision(request.base_ref))
    return args


def validated_git_revision(value: str) -> str:
    """Reject revision text that Git could interpret as an option."""

    if (
        not value
        or value.strip() != value
        or value.startswith("-")
        or any(character.isspace() or not character.isprintable() for character in value)
    ):
        raise ValueError("base ref must be a non-option Git revision without whitespace")
    return value


def run_git(args: list[str]) -> str:
    """Run Git command and return stdout."""

    result = subprocess.run(  # nosec B603
        args,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout
