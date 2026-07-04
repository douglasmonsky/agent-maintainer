"""Repository discovery helpers for agent hooks."""

from __future__ import annotations

import shutil
import subprocess  # nosec B404
from pathlib import Path


def discover_repo_root(cwd: Path) -> Path:
    """Return the Git repository root for hook execution."""
    git_path = shutil.which("git")
    if git_path is None:
        return cwd
    result = subprocess.run(  # nosec B603
        [git_path, "rev-parse", "--show-toplevel"],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip())
    return cwd


def command_available(command: str) -> bool:
    """Return whether a command is available on PATH."""
    return shutil.which(command) is not None
