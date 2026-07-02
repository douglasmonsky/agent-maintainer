"""Parse Git diffs into changed HEAD line spans."""

from __future__ import annotations

import re
import subprocess  # nosec B404
from dataclasses import dataclass
from pathlib import Path

from docsync.core.models import LineSpan

HUNK_RE = re.compile(
    r"@@ -(?P<old>\d+)(?:,(?P<old_count>\d+))? \+(?P<new>\d+)(?:,(?P<new_count>\d+))? @@"
)


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
    command = ["git", "diff", "--unified=0", "--no-ext-diff", base_ref, "--"]
    completed = subprocess.run(  # nosec B603
        command,
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise GitDiffError(completed.stderr.strip() or "git diff failed")
    return completed.stdout


def _new_path(line: str) -> Path | None:
    raw_path = line.removeprefix("+++ ").strip()
    if raw_path == "/dev/null":
        return None
    if raw_path.startswith("b/"):
        raw_path = raw_path[2:]
    return Path(raw_path)
