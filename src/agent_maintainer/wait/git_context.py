"""Local Git identity helpers for wait registration."""

from __future__ import annotations

import shutil
import subprocess  # nosec B404 - fixed git executable with bounded arguments.
from pathlib import Path


def complete_git_identity(
    root: Path,
    *,
    branch: str,
    head_sha: str,
) -> tuple[str, str]:
    """Fill missing branch and head SHA from the local checkout."""

    return (
        branch or _git_output(root, "branch", "--show-current"),
        head_sha or _git_output(root, "rev-parse", "HEAD"),
    )


def _git_output(root: Path, *args: str) -> str:
    command = [shutil.which("git") or "git", *args]
    try:
        result = subprocess.run(  # nosec B603 - command uses fixed git executable.
            command,
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""
    return result.stdout.strip()
