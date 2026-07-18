"""Neutral git change readers for provider-aware advisory reports."""

from __future__ import annotations

import re
import shutil
import subprocess  # nosec B404
from dataclasses import dataclass
from pathlib import Path

from agent_maintainer.core.repo_paths import RepoPathError, validate_repo_path

NUMSTAT_FIELD_COUNT = 3
GIT_SHA = re.compile(r"^[0-9a-f]{40,64}$")
SINGLE_PATH_STATUSES = {
    "A": "added",
    "D": "deleted",
    "M": "modified",
    "T": "type-changed",
    "U": "unmerged",
}
PAIR_PATH_STATUSES = {"C": "copied", "R": "renamed"}


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


@dataclass(frozen=True)
class GitPathChange:
    """Structured Git path identity for one add, edit, move, copy, or delete."""

    path: str
    kind: str
    old_path: str | None = None

    def affected_paths(self) -> tuple[str, ...]:
        """Return every source or destination path affected by the change."""
        return (self.old_path, self.path) if self.old_path is not None else (self.path,)

    def evidence_paths(self) -> tuple[str, ...]:
        """Return paths present after the change that may satisfy evidence."""
        return () if self.kind == "deleted" else (self.path,)


def git_numstat_command(base_ref: str, *, staged: bool) -> list[str]:
    """Build neutral git numstat command without ecosystem filters."""
    git = shutil.which("git") or "git"
    command = [git, "diff", "--numstat", "-C", "--find-copies-harder"]
    command.extend(["--cached"] if staged else [base_ref])
    command.append("--")
    return command


def git_name_status_command(base_sha: str, *, staged: bool) -> list[str]:
    """Build NUL-delimited structured path-change command."""
    git = shutil.which("git") or "git"
    command = [
        git,
        "diff",
        "--name-status",
        "-z",
        "-M",
        "-C",
        "--find-copies-harder",
    ]
    if staged:
        return [*command, "--cached", "--"]
    if not GIT_SHA.fullmatch(base_sha):
        raise ValueError("base SHA must be a resolved hexadecimal object ID")
    return [*command, f"{base_sha}...HEAD", "--"]


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


def run_git_name_status(
    base_ref: str,
    *,
    staged: bool,
    cwd: Path | None = None,
) -> tuple[GitPathChange, ...]:
    """Read structured Git path changes without option-shaped ref ambiguity."""
    base_sha = "" if staged else _resolve_base_sha(base_ref, cwd=cwd)
    try:
        command = git_name_status_command(base_sha, staged=staged)
        if cwd is None:
            result = subprocess.run(  # nosec B603
                command,
                text=False,
                capture_output=True,
                check=True,
            )
        else:
            result = subprocess.run(  # nosec B603
                command,
                text=False,
                capture_output=True,
                check=True,
                cwd=cwd,
            )
        return parse_name_status_z(result.stdout)
    except subprocess.CalledProcessError as exc:
        stderr = _stderr_text(exc.stderr)
        target = diff_target_label(base_ref, staged=staged)
        raise RuntimeError(f"Could not calculate path changes for {target}: {stderr}") from exc
    except (UnicodeError, ValueError) as exc:
        target = diff_target_label(base_ref, staged=staged)
        raise RuntimeError(f"Invalid Git path changes for {target}: {exc}") from exc


def parse_name_status_z(output: bytes) -> tuple[GitPathChange, ...]:
    """Parse `git diff --name-status -z` bytes exactly once."""
    if not output:
        return ()
    if not output.endswith(b"\0"):
        raise ValueError("name-status output must end with NUL")
    tokens = output[:-1].split(b"\0")
    changes: list[GitPathChange] = []
    index = 0
    while index < len(tokens):
        status = _decode_status(tokens[index])
        index += 1
        status_code = status[0]
        if status_code in PAIR_PATH_STATUSES:
            if not status[1:].isdigit() or index + 1 >= len(tokens):
                raise ValueError(f"invalid paired name-status record: {status!r}")
            old_path = _decode_git_path(tokens[index])
            path = _decode_git_path(tokens[index + 1])
            index += 2
            changes.append(
                GitPathChange(path, PAIR_PATH_STATUSES[status_code], old_path=old_path),
            )
            continue
        if status not in SINGLE_PATH_STATUSES or index >= len(tokens):
            raise ValueError(f"invalid name-status record: {status!r}")
        path = _decode_git_path(tokens[index])
        index += 1
        changes.append(GitPathChange(path, SINGLE_PATH_STATUSES[status]))
    return tuple(changes)


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


def _resolve_base_sha(base_ref: str, *, cwd: Path | None = None) -> str:
    git = shutil.which("git") or "git"
    command = [
        git,
        "rev-parse",
        "--verify",
        "--end-of-options",
        f"{base_ref}^{{commit}}",
    ]
    try:
        if cwd is None:
            result = subprocess.run(  # nosec B603
                command,
                text=True,
                capture_output=True,
                check=True,
            )
        else:
            result = subprocess.run(  # nosec B603
                command,
                text=True,
                capture_output=True,
                check=True,
                cwd=cwd,
            )
    except subprocess.CalledProcessError as exc:
        stderr = _stderr_text(exc.stderr)
        raise RuntimeError(f"Could not resolve base ref {base_ref!r}: {stderr}") from exc
    sha = result.stdout.strip()
    if not GIT_SHA.fullmatch(sha):
        raise RuntimeError(f"Could not resolve base ref {base_ref!r}: invalid object ID")
    return sha


def _decode_status(value: bytes) -> str:
    try:
        return value.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("name-status code must be ASCII") from exc


def _decode_git_path(value: bytes) -> str:
    try:
        path = value.decode("utf-8")
        return validate_repo_path(path, label="Git path")
    except (UnicodeDecodeError, RepoPathError) as exc:
        raise ValueError(str(exc)) from exc


def _stderr_text(stderr: str | bytes | None) -> str:
    if isinstance(stderr, bytes):
        return stderr.decode("utf-8", errors="replace").strip() or "unknown git failure"
    return stderr.strip() if stderr else "unknown git failure"
