"""Shared Git and path safety for explicit assessment baseline lifecycles."""

from __future__ import annotations

import re
import subprocess  # nosec B404 - fixed local Git inspection commands only
from pathlib import Path

COMMIT_PATTERN = re.compile(r"[0-9a-f]{7,64}")


class BaselineRepositoryError(ValueError):
    """An invalid repository state for an explicit baseline operation."""


def repository_root(target: Path) -> Path:
    """Return a validated repository root with an immutable Git identity."""
    try:
        root = target.resolve(strict=True)
    except OSError as exc:
        raise BaselineRepositoryError(f"invalid target repository: {exc}") from exc
    if not root.is_dir():
        raise BaselineRepositoryError(f"target repository is not a directory: {root}")
    repository_head(root)
    return root


def repository_head(target: Path) -> str:
    """Return the normalized HEAD commit for one repository."""
    completed = _run_git(target, "rev-parse", "HEAD")
    head = completed.stdout.strip().lower()
    if completed.returncode != 0 or COMMIT_PATTERN.fullmatch(head) is None:
        raise BaselineRepositoryError("target must be a Git repository with a valid HEAD")
    return head


def require_clean_worktree(target: Path, *, operation: str) -> None:
    """Reject lifecycle writes when any tracked or untracked state is present."""
    completed = _run_git(target, "status", "--porcelain", "--untracked-files=all")
    if completed.returncode != 0:
        raise BaselineRepositoryError("could not inspect target Git worktree")
    if completed.stdout:
        raise BaselineRepositoryError(f"{operation} changes require a clean Git worktree")


def confined_path(target: Path, configured: Path, *, label: str) -> Path:
    """Resolve one configured lifecycle path without escaping its repository."""
    candidate = configured if configured.is_absolute() else target / configured
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(target)
    except ValueError as exc:
        raise BaselineRepositoryError(f"{label} path escapes the target repository") from exc
    return resolved


def _run_git(target: Path, *args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(  # nosec B603
            ("git", "-C", str(target), *args),
            check=False,
            capture_output=True,
            text=True,
            shell=False,
        )
    except OSError as exc:
        raise BaselineRepositoryError(f"could not run Git: {exc}") from exc
