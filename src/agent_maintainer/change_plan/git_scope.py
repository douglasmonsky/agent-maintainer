"""Validate Git diff scope against cohesive change plans."""

from __future__ import annotations

import fnmatch
import shutil
import subprocess  # nosec B404
from pathlib import Path

from agent_maintainer.change_plan.models import ChangedPath, ChangePlan, ValidationIssue

NUMSTAT_FIELD_COUNT = 3


def git_changes(repo_root: Path, *, base_ref: str, staged: bool = False) -> tuple[ChangedPath, ...]:
    """Return changed paths from Git numstat."""

    result = subprocess.run(  # nosec B603
        git_numstat_command(base_ref, staged=staged),
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return parse_numstat(result.stdout)


def git_numstat_command(base_ref: str, *, staged: bool) -> list[str]:
    """Return Git numstat command."""

    command = [shutil.which("git") or "git", "diff", "--numstat"]
    command.extend(["--cached"] if staged else [base_ref])
    command.append("--")
    return command


def current_branch(repo_root: Path) -> str:
    """Return current Git branch name, or empty string when detached."""

    result = subprocess.run(  # nosec B603
        [shutil.which("git") or "git", "branch", "--show-current"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def parse_numstat(output: str) -> tuple[ChangedPath, ...]:
    """Parse Git numstat output."""

    changes: list[ChangedPath] = []
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) != NUMSTAT_FIELD_COUNT or "-" in parts[:2]:
            continue
        added_raw, deleted_raw, path = parts
        changes.append(ChangedPath(path=path, added=int(added_raw), deleted=int(deleted_raw)))
    return tuple(changes)


def scope_issues(plan: ChangePlan, changes: tuple[ChangedPath, ...]) -> tuple[ValidationIssue, ...]:
    """Return change-scope issues for a plan."""

    issues: list[ValidationIssue] = []
    for file_change in changes:
        issues.extend(path_issues(plan, file_change))
    changed_lines = sum(item.changed_lines for item in changes)
    if len(changes) > plan.metadata.max_changed_files:
        file_limit = plan.metadata.max_changed_files
        issues.append(
            scope_issue(
                plan,
                f"changed file count {len(changes)} exceeds plan limit {file_limit}",
            )
        )
    if changed_lines > plan.metadata.max_changed_lines:
        line_limit = plan.metadata.max_changed_lines
        issues.append(
            scope_issue(
                plan,
                f"changed line count {changed_lines} exceeds plan limit {line_limit}",
            )
        )
    if source_change_requires_tests(plan, changes):
        issues.append(scope_issue(plan, "source changes require a test change"))
    return tuple(issues)


def path_issues(plan: ChangePlan, change: ChangedPath) -> tuple[ValidationIssue, ...]:
    """Return allowlist and denylist issues for one path."""

    issues: list[ValidationIssue] = []
    if path_matches_any(change.path, plan.metadata.forbidden_paths):
        issues.append(scope_issue(plan, f"forbidden path changed: {change.path}"))
    if not path_matches_any(change.path, plan.metadata.allowed_paths):
        issues.append(scope_issue(plan, f"path outside allowed scope: {change.path}"))
    return tuple(issues)


def source_change_requires_tests(plan: ChangePlan, changes: tuple[ChangedPath, ...]) -> bool:
    """Return whether source-only change violates plan test policy."""

    if not plan.metadata.requires_tests or plan.metadata.allow_source_without_test_change:
        return False
    return any(is_source_path(change.path) for change in changes) and not any(
        is_test_path(change.path) for change in changes
    )


def is_source_path(path: str) -> bool:
    """Return whether path is likely source code."""

    return path.endswith(".py") and not is_test_path(path)


def is_test_path(path: str) -> bool:
    """Return whether path is likely test code."""

    name = path.rsplit("/", 1)[-1]
    return path.startswith("tests/") or "/tests/" in path or name.startswith("test_")


def path_matches_any(path: str, patterns: tuple[str, ...]) -> bool:
    """Return whether path matches at least one glob pattern."""

    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def scope_issue(plan: ChangePlan, message: str) -> ValidationIssue:
    """Return scope issue object for a plan."""

    return ValidationIssue(path=plan.path.as_posix(), message=message)
