"""Compact Git state helpers for verifier artifacts."""

from __future__ import annotations

import shutil
import subprocess  # nosec B404
from pathlib import Path


def git_state(repo_root: Path) -> dict[str, object]:
    """Return compact Git metadata for the current repository."""

    return {
        "sha": git_output(repo_root, ("rev-parse", "HEAD")),
        "branch": git_output(repo_root, ("branch", "--show-current")),
        "dirty": bool(git_output(repo_root, ("status", "--short"))),
    }


def git_output(repo_root: Path, args: tuple[str, ...]) -> str:
    """Return stripped Git command output, or an empty string on failure."""

    git_path = shutil.which("git")
    if git_path is None:
        return ""
    completed = subprocess.run(  # nosec B603
        [git_path, *args],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()
