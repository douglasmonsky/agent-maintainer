"""Doctor checks for local repository and Git environment."""

from __future__ import annotations

import shutil
import subprocess  # nosec B404
from pathlib import Path

from agent_maintainer.doctor.support import models as doctor_models

DoctorResult = doctor_models.DoctorResult
OK = doctor_models.OK
WARNING = doctor_models.WARNING
ERROR = doctor_models.ERROR


def check_repo_root(repo_root: Path) -> DoctorResult:
    """Check files that identify a usable Agent Maintainer repository root."""

    missing = [path for path in (".git",) if not (repo_root / path).exists()]
    if missing:
        missing_paths = ", ".join(missing)
        return DoctorResult(
            "repo-root",
            ERROR,
            f"Missing required repo paths: {missing_paths}",
            state=doctor_models.MISSING,
        )
    if not (repo_root / "pyproject.toml").exists():
        return DoctorResult(
            "repo-root",
            WARNING,
            "pyproject.toml is absent; defaults will be used.",
            state=doctor_models.MISSING,
        )
    return DoctorResult("repo-root", OK, str(repo_root))


def check_virtualenv(repo_root: Path) -> DoctorResult:
    """Report whether a local virtualenv is available for tool execution."""

    for relative in (".venv/bin/python", "venv/bin/python"):
        if (repo_root / relative).exists():
            return DoctorResult("virtualenv", OK, relative)
    return DoctorResult(
        "virtualenv",
        WARNING,
        "No .venv or venv Python found.",
        state=doctor_models.MISSING,
        hint="Run python3 -m agent_maintainer bootstrap.",
    )


def check_git_state(repo_root: Path) -> DoctorResult:
    """Summarize dirty, ahead, and behind Git state."""

    git_path = find_git()
    if git_path is None:
        return git_missing_result()

    completed = run_git_status(repo_root, git_path)
    if completed.returncode != 0:
        return DoctorResult(
            "git-state",
            WARNING,
            (completed.stderr or "git status failed").strip(),
        )
    return git_status_result(completed.stdout)


def find_git() -> str | None:
    """Return the Git executable path when available."""

    return shutil.which("git")


def git_missing_result() -> DoctorResult:
    """Return the diagnostic row for a missing Git executable."""

    return DoctorResult(
        "git-state",
        WARNING,
        "git executable was not found.",
        state=doctor_models.MISSING,
    )


def run_git_status(repo_root: Path, git_path: str) -> subprocess.CompletedProcess[str]:
    """Run the Git status command used by doctor."""

    return subprocess.run(  # nosec B603
        [git_path, "status", "--short", "--branch"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )


def git_status_result(stdout: str) -> DoctorResult:
    """Return a diagnostic row from porcelain branch status output."""

    lines = stdout.splitlines()
    branch = lines[0] if lines else "## unknown"
    details = git_state_details(branch, changed_count=max(0, len(lines) - 1))
    if details:
        hint = (
            "Set a new upstream or unset the stale tracking branch." if "[gone]" in branch else ""
        )
        return DoctorResult("git-state", WARNING, "; ".join(details), hint=hint)
    return DoctorResult("git-state", OK, branch.removeprefix("## "))


def git_state_details(branch: str, *, changed_count: int) -> list[str]:
    """Return warning details for ahead, behind, or dirty Git state."""

    details: list[str] = []
    if "[ahead" in branch or "[behind" in branch or "[gone]" in branch:
        details.append(branch.removeprefix("## "))
    if changed_count > 0:
        details.append(f"{changed_count} changed path(s)")
    return details
