"""Parse Git diffs into changed HEAD line spans."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from docsync.core.models import LineSpan
from docsync.git.process import (
    DEFAULT_GIT_TIMEOUT_SECONDS,
    DEFAULT_MAX_GIT_STDOUT_BYTES,
    GitProcessError,
    GitProcessResult,
    run_git,
)

HUNK_RE = re.compile(
    r"@@ -(?P<old>\d+)(?:,(?P<old_count>\d+))? \+(?P<new>\d+)(?:,(?P<new_count>\d+))? @@"
)
GIT_TIMEOUT_SECONDS = DEFAULT_GIT_TIMEOUT_SECONDS
MAX_GIT_OUTPUT_BYTES = DEFAULT_MAX_GIT_STDOUT_BYTES


@dataclass(frozen=True)
class GitDiffError(ValueError):
    """Raised when Git diff data cannot be loaded."""

    message: str


def changed_line_spans(repo_root: Path, base_ref: str) -> tuple[LineSpan, ...]:
    """Return changed line spans in current working tree coordinates."""
    diff_text = _git_diff(repo_root, base_ref)
    return parse_changed_line_spans(diff_text)


def parse_changed_line_spans(diff_text: str) -> tuple[LineSpan, ...]:
    """Parse `git diff --unified=0` output into changed HEAD spans."""
    spans: list[LineSpan] = []
    current_path: Path | None = None
    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            current_path = _new_path(line)
            continue
        if current_path is None or not line.startswith("@@ "):
            continue
        match = HUNK_RE.search(line)
        if match is None:
            continue
        new_count = int(match.group("new_count") or "1")
        if new_count == 0:
            continue
        start_line = int(match.group("new"))
        spans.append(
            LineSpan(
                path=current_path,
                start_line=start_line,
                end_line=start_line + new_count - 1,
            )
        )
    return tuple(spans)


def _git_diff(repo_root: Path, base_ref: str) -> str:
    _validate_revision(base_ref)
    errors: list[str] = []
    for candidate in _base_ref_candidates(repo_root, base_ref):
        _validate_revision(candidate)
        command = [
            "git",
            "diff",
            "--unified=0",
            "--no-ext-diff",
            "--no-textconv",
            candidate,
            "--",
        ]
        completed = _run_git(repo_root, tuple(command[1:]))
        if completed.returncode == 0:
            return completed.stdout
        errors.append(_git_error(candidate, completed.stderr))
    raise GitDiffError("; ".join(errors) or "git diff failed")


def _validate_revision(value: str) -> None:
    """Reject revision text that Git could interpret as an option."""

    if (
        not value
        or value.strip() != value
        or value.startswith("-")
        or any(character.isspace() or not character.isprintable() for character in value)
    ):
        raise GitDiffError("base ref must be a non-option Git revision without whitespace")


def _git_error(candidate: str, stderr: str) -> str:
    message = stderr.strip() or "git diff failed"
    return f"{candidate}: {message}"


def _base_ref_candidates(repo_root: Path, base_ref: str) -> tuple[str, ...]:
    if base_ref != "origin/main":
        return (base_ref,)
    candidates = ["origin/main"]
    upstream = _git_output(
        repo_root,
        ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"),
    )
    if upstream:
        candidates.append(upstream)
    candidates.extend(("main", "master", "HEAD"))
    return tuple(dict.fromkeys(candidates))


def _git_output(repo_root: Path, args: tuple[str, ...]) -> str:
    try:
        completed = _run_git(repo_root, args)
    except GitDiffError:
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def _run_git(repo_root: Path, args: tuple[str, ...]) -> GitProcessResult:
    try:
        return run_git(
            repo_root,
            args,
            timeout_seconds=GIT_TIMEOUT_SECONDS,
            max_stdout_bytes=MAX_GIT_OUTPUT_BYTES,
        )
    except GitProcessError as exc:
        raise GitDiffError(str(exc)) from exc


def _new_path(line: str) -> Path | None:
    raw_path = line.removeprefix("+++ ").strip()
    if raw_path == "/dev/null":
        return None
    if raw_path.startswith("b/"):
        raw_path = raw_path[2:]
    return Path(raw_path)
