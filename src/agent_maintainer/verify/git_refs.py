"""Git reference validation for verifier inputs."""

from __future__ import annotations

import shutil
import subprocess  # nosec B404
from pathlib import Path


def ref_failures(
    repo_root: Path,
    *,
    base_ref: str,
    compare_branch: str,
    validate_compare_branch: bool,
) -> tuple[str, ...]:
    """Return verifier Git reference validation failures."""

    if not (repo_root / ".git").exists():
        return ()
    git_path = shutil.which("git")
    if git_path is None:
        return ("git executable was not found; cannot validate --base-ref.",)
    ref_checks = [("--base-ref", base_ref)]
    if validate_compare_branch:
        ref_checks.append(("--compare-branch", compare_branch))
    failures = [
        failure
        for label, ref in ref_checks
        if (failure := validate_ref(repo_root, git_path, label, ref)) is not None
    ]
    return tuple(failures)


def validate_ref(repo_root: Path, git_path: str, label: str, ref: str) -> str | None:
    """Return an error message when one Git ref is invalid."""

    if not ref or ref.strip() != ref:
        return f"{label} must be a non-empty Git ref without surrounding whitespace."
    completed = subprocess.run(  # nosec B603
        [
            git_path,
            "rev-parse",
            "--verify",
            "--quiet",
            "--end-of-options",
            f"{ref}^{{commit}}",
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode == 0:
        return None
    return f"{label} {ref!r} is not a valid commit ref."
