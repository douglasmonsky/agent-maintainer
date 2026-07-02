"""Neutral git change readers for provider-aware advisory reports."""

from __future__ import annotations

import shutil
import subprocess  # nosec B404
from dataclasses import dataclass

NUMSTAT_FIELD_COUNT = 3


@dataclass(frozen=True)
class FileChange:
    """Git numstat summary for one changed path."""

    path: str
    added: int
    deleted: int

    @property
    def changed(self) -> int:
        """Return total changed lines, excluding binary unknown counts."""
        return self.added + self.deleted


def git_numstat_command(base_ref: str, *, staged: bool) -> list[str]:
    """Build neutral git numstat command without ecosystem filters."""
    git = shutil.which("git") or "git"
    command = [git, "diff", "--numstat", "-C", "--find-copies-harder"]
    command.extend(["--cached"] if staged else [base_ref])
    command.append("--")
    return command


def diff_target_label(base_ref: str, *, staged: bool) -> str:
    """Return diff target label for error messages."""
    return "staged changes" if staged else repr(base_ref)


def run_git_numstat(base_ref: str, *, staged: bool) -> list[FileChange]:
    """Read neutral git numstat output for provider-aware assessment."""
    try:
        result = subprocess.run(  # nosec B603
            git_numstat_command(base_ref, staged=staged),
            text=True,
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else "unknown git diff failure"
        target = diff_target_label(base_ref, staged=staged)
        raise RuntimeError(f"Could not calculate diff stats for {target}: {stderr}") from exc
    return [
        parsed
        for line in result.stdout.splitlines()
        if (parsed := parse_numstat_line(line)) is not None
    ]


def parse_numstat_line(line: str) -> FileChange | None:
    """Parse one git numstat line without path-name exclusions."""
    parts = line.split("\t")
    if len(parts) != NUMSTAT_FIELD_COUNT:
        return None
    added, deleted, path = parts
    return FileChange(
        path=path,
        added=parse_count(added),
        deleted=parse_count(deleted),
    )


def parse_count(value: str) -> int:
    """Return numeric numstat count, treating binary '-' counts as zero."""
    return int(value) if value.isdecimal() else 0
