"""Test relevance guidance for change-budget warnings."""

from __future__ import annotations

import argparse
import shutil
import subprocess  # nosec B404
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.test_intel.mapping import likely_tests_for_changes

MISSING_TEST_CHANGE_WARNING = "Source changed without likely relevant test changes."
IRRELEVANT_TEST_CHANGE_WARNING = (
    "A test file changed, but no likely relevant test changed for modified source."
)
DOCSYNC_EVIDENCE_MARKER_PREFIX = "# docsync:evidence."


def warnings_for_changes(
    args: argparse.Namespace,
    config: MaintainerConfig,
    py_source_changes: Sequence[object],
    py_test_changes: Sequence[object],
    repo_root: Path | None,
) -> list[str]:
    """Return warnings for source changes without likely relevant tests."""

    if not should_warn_about_tests(args, config, py_source_changes):
        return []
    source_paths = change_paths(py_source_changes)
    if source_changes_are_docsync_trace_only(args, repo_root or Path.cwd(), source_paths):
        return []
    likely_tests = likely_test_paths(source_paths, config, repo_root or Path.cwd())
    changed_tests = set(change_paths(py_test_changes))
    if changed_tests.intersection(likely_tests):
        return []
    if changed_tests:
        return [irrelevant_test_warning(args, likely_tests)]
    return [missing_test_warning(args, likely_tests)]


def should_warn_about_tests(
    args: argparse.Namespace,
    config: MaintainerConfig,
    py_source_changes: Sequence[object],
) -> bool:
    """Return whether source-without-test warning is active."""

    return bool(
        py_source_changes and config.require_tests and not args.allow_source_without_test_change
    )


def change_paths(changes: Sequence[object]) -> tuple[str, ...]:
    """Return path values from changed-file objects."""

    return tuple(str(cast(Any, change).path) for change in changes)


def source_changes_are_docsync_trace_only(
    args: argparse.Namespace,
    repo_root: Path,
    source_paths: tuple[str, ...],
) -> bool:
    """Return whether source diffs only add/remove DocSync evidence markers."""

    lines = changed_source_lines(args, repo_root, source_paths)
    if not lines:
        return False
    return all(is_docsync_trace_line(line) for line in lines)


def changed_source_lines(
    args: argparse.Namespace,
    repo_root: Path,
    source_paths: tuple[str, ...],
) -> tuple[str, ...]:
    """Return added/removed non-context source lines for changed source paths."""

    git = shutil.which("git") or "git"
    command = [git, "diff", "--unified=0", "--no-ext-diff"]
    command.extend(["--cached"] if args.staged else [args.base_ref])
    command.append("--")
    command.extend(source_paths)
    try:
        result = subprocess.run(  # nosec B603
            command,
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return ()
    return tuple(diff_changed_content_lines(result.stdout))


def diff_changed_content_lines(diff_output: str) -> tuple[str, ...]:
    """Return added/removed content lines from a unified diff."""

    changed: list[str] = []
    for line in diff_output.splitlines():
        if not line.startswith(("+", "-")):
            continue
        if line.startswith(("+++", "---")):
            continue
        content = line[1:].strip()
        if content:
            changed.append(content)
    return tuple(changed)


def is_docsync_trace_line(line: str) -> bool:
    """Return whether one changed source line is DocSync trace metadata."""

    return line.startswith(DOCSYNC_EVIDENCE_MARKER_PREFIX)


def likely_test_paths(
    source_paths: tuple[str, ...],
    config: MaintainerConfig,
    repo_root: Path,
) -> tuple[str, ...]:
    """Return unique likely test paths for changed source."""

    paths = {match.test_path for match in likely_tests_for_changes(source_paths, config, repo_root)}
    return tuple(sorted(paths))


def missing_test_warning(args: argparse.Namespace, likely_tests: tuple[str, ...]) -> str:
    """Return actionable warning for source changes without test changes."""

    return "\n".join(
        (
            MISSING_TEST_CHANGE_WARNING,
            f"Likely test files: {format_likely_tests(likely_tests)}",
            f"Run: {test_intel_command(args)}",
        )
    )


def irrelevant_test_warning(args: argparse.Namespace, likely_tests: tuple[str, ...]) -> str:
    """Return actionable warning for irrelevant test changes."""

    return "\n".join(
        (
            IRRELEVANT_TEST_CHANGE_WARNING,
            f"Likely test files: {format_likely_tests(likely_tests)}",
            f"Run: {test_intel_command(args)}",
        )
    )


def format_likely_tests(likely_tests: tuple[str, ...]) -> str:
    """Return compact likely-test list for warnings."""

    return " ".join(likely_tests) if likely_tests else "<none>"


def test_intel_command(args: argparse.Namespace) -> str:
    """Return command to expand test intelligence guidance."""

    command = ["python", "-m", "agent_maintainer", "test-intel", "changed"]
    command.extend(["--staged"] if args.staged else ["--base-ref", args.base_ref])
    return " ".join(command)


def has_warning(warnings: list[str]) -> bool:
    """Return whether warnings include source/test relevance guidance."""

    prefixes = (MISSING_TEST_CHANGE_WARNING, IRRELEVANT_TEST_CHANGE_WARNING)
    return any(warning.startswith(prefixes) for warning in warnings)
