"""Changed-line helpers for test-intelligence coverage."""

from __future__ import annotations

import re
import shutil
import subprocess  # nosec B404
from collections.abc import Iterable, Mapping
from pathlib import Path

HUNK_HEADER_PATTERN = re.compile(r"^@@ -\d+(?:,\d+)? \+(?P<start>\d+)(?:,\d+)? @@")
PERCENT_SCALE = 100.0


def changed_line_numbers(
    repo_root: Path,
    changed_source: tuple[str, ...],
    *,
    base_ref: str,
    staged: bool,
) -> dict[str, frozenset[int]]:
    """Return changed new-file line numbers for configured source files."""
    if not changed_source:
        return {}

    command = git_diff_command(changed_source, base_ref=base_ref, staged=staged)
    try:
        result = subprocess.run(  # nosec B603
            command,
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return {}
    return parse_changed_lines(result.stdout, frozenset(changed_source))


def git_diff_command(
    changed_source: tuple[str, ...],
    *,
    base_ref: str,
    staged: bool,
) -> list[str]:
    """Build zero-context git diff command for changed source paths."""
    git = shutil.which("git") or "git"
    command = [git, "diff", "--unified=0"]
    command.extend(["--cached"] if staged else [base_ref])
    command.extend(["--", *changed_source])
    return command


def parse_changed_lines(
    diff_text: str,
    changed_source: frozenset[str],
) -> dict[str, frozenset[int]]:
    """Return changed new-file line numbers from unified diff text."""
    changed_lines: dict[str, set[int]] = {source: set() for source in changed_source}
    current_path: str | None = None
    current_line: int | None = None

    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            current_path = normalize_diff_path(line[4:].strip(), changed_source)
            current_line = None
            continue
        if line.startswith("@@ "):
            current_line = hunk_start(line) if current_path else None
            continue
        current_line = record_diff_line(
            line,
            current_path=current_path,
            current_line=current_line,
            changed_lines=changed_lines,
        )

    return {source: frozenset(lines) for source, lines in changed_lines.items() if lines}


def record_diff_line(
    line: str,
    *,
    current_path: str | None,
    current_line: int | None,
    changed_lines: dict[str, set[int]],
) -> int | None:
    """Record one content diff line and return next new-file line number."""
    if current_path is None or current_line is None:
        return current_line
    if line.startswith("+"):
        changed_lines[current_path].add(current_line)
        return current_line + 1
    if line.startswith(" "):
        return current_line + 1
    return current_line


def normalize_diff_path(raw_path: str, changed_source: frozenset[str]) -> str | None:
    """Return normalized target path when it belongs to changed source."""
    normalized = raw_path.removeprefix("b/")
    if normalized == "/dev/null" or normalized not in changed_source:
        return None
    return normalized


def hunk_start(line: str) -> int | None:
    """Return new-file hunk start line."""
    match = HUNK_HEADER_PATTERN.match(line)
    if match is None:
        return None
    return int(match.group("start"))


def line_coverage_percent(
    changed_lines: Iterable[int],
    covered_lines: frozenset[int],
    missing_lines: frozenset[int],
) -> float | None:
    """Return coverage percent for changed executable lines."""
    changed_set = frozenset(changed_lines)
    covered = changed_set & covered_lines
    missing = changed_set & missing_lines
    denominator = len(covered) + len(missing)
    if denominator == 0:
        return None
    return round((len(covered) / denominator) * PERCENT_SCALE, 2)


def int_line_set(payload: object) -> frozenset[int]:
    """Return integer line numbers from coverage artifact payload."""
    if not isinstance(payload, list):
        return frozenset()
    return frozenset(item for item in payload if isinstance(item, int))


def changed_line_map(
    changed_lines: Mapping[str, frozenset[int]] | None,
) -> Mapping[str, frozenset[int]]:
    """Return a non-null changed-line mapping."""
    return changed_lines or {}
