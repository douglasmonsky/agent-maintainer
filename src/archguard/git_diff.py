"""Git diff path discovery for architecture policy checks."""

from __future__ import annotations

import shutil
import subprocess  # nosec B404: subprocess is used for fixed git commands.
from pathlib import Path


def git_name_only_command(base_ref: str, *, staged: bool) -> list[str]:
    """Build the git command that lists changed path names."""
    git = shutil.which("git") or "git"
    command = [git, "diff", "--name-only"]
    command.extend(["--cached"] if staged else [base_ref])
    command.append("--")
    return command


def changed_paths(repo_root: Path, *, base_ref: str, staged: bool) -> tuple[str, ...]:
    """Return normalized changed paths for staged changes or a base ref diff."""
    try:
        result = subprocess.run(  # nosec B603: command shape is fixed to git diff.
            git_name_only_command(base_ref, staged=staged),
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else "unknown git diff failure"
        target = "staged changes" if staged else repr(base_ref)
        raise RuntimeError(f"Could not calculate changed paths for {target}: {stderr}") from exc

    return tuple(
        line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()
    )
