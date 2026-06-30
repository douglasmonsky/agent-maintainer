"""Run advisory mutation sweep candidates in copied worktrees."""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404
import sys
import tempfile
import time
from pathlib import Path

from agent_maintainer.runners import mutmut_stats
from agent_maintainer.test_intel.mutation_sweep import MutationSweepCandidate
from agent_maintainer.test_intel.mutation_sweep_config import patch_mutmut_config
from agent_maintainer.test_intel.mutation_sweep_execution import (
    MutationSweepCandidateResult,
    MutationSweepExecutionRequest,
)

MUTMUT_STATS_PATH = Path("mutants/mutmut-cicd-stats.json")
COPY_IGNORE_NAMES = (
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".semgrep",
    ".venv",
    ".verify-logs",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
    "mutants",
    "node_modules",
    "venv",
)


def execute_candidate(
    candidate: MutationSweepCandidate,
    index: int,
    artifact_dir: Path,
    request: MutationSweepExecutionRequest,
) -> MutationSweepCandidateResult:
    """Execute one candidate and collect artifact files."""

    candidate_dir = artifact_dir / candidate_dir_name(index)
    candidate_dir.mkdir(parents=True)
    started_at = time.monotonic()
    try:
        return execute_candidate_with_worktree(candidate, index, candidate_dir, request)
    except (OSError, ValueError) as exc:
        run_log = candidate_dir / "mutmut-run.log"
        run_log.write_text(str(exc), encoding="utf-8")
        return MutationSweepCandidateResult(
            candidate=candidate,
            index=index,
            status="failed",
            duration_seconds=time.monotonic() - started_at,
            run_returncode=1,
            export_returncode=None,
            promotion_ready=False,
            stats=None,
            run_log=run_log,
            export_log=None,
            stats_path=None,
            worktree_path=None,
            error=str(exc),
        )


def execute_candidate_with_worktree(
    candidate: MutationSweepCandidate,
    index: int,
    candidate_dir: Path,
    request: MutationSweepExecutionRequest,
) -> MutationSweepCandidateResult:
    """Copy the repo, patch temp config, run Mutmut, and collect stats."""

    if request.keep_worktree:
        worktree = candidate_dir / "worktree"
        copy_repo(request.repo_root, worktree)
        return run_candidate_in_worktree(candidate, index, candidate_dir, worktree, request)
    with tempfile.TemporaryDirectory(prefix="agent-maintainer-mutmut-") as temp_dir:
        worktree = Path(temp_dir) / "repo"
        copy_repo(request.repo_root, worktree)
        return run_candidate_in_worktree(candidate, index, candidate_dir, worktree, request)


def copy_repo(repo_root: Path, destination: Path) -> None:
    """Copy source checkout while skipping generated and heavyweight paths."""

    ignore = shutil.ignore_patterns(*COPY_IGNORE_NAMES, "*.pyc", "* 2*", "* copy*")
    shutil.copytree(repo_root, destination, ignore=ignore)
    initialize_git_snapshot(destination)


def initialize_git_snapshot(worktree: Path) -> None:
    """Create local Git metadata for tests that inspect repository state."""

    if worktree.joinpath(".git").exists():
        return
    run_git_snapshot_command(("git", "init", "-b", "main"), worktree)
    run_git_snapshot_command(("git", "add", "-A"), worktree)
    run_git_snapshot_command(
        (
            "git",
            "-c",
            "user.email=agent-maintainer@example.invalid",
            "-c",
            "user.name=Agent Maintainer",
            "commit",
            "-m",
            "mutation sweep snapshot",
        ),
        worktree,
    )


def run_git_snapshot_command(command: tuple[str, ...], worktree: Path) -> None:
    """Run one Git snapshot command."""

    subprocess.run(  # nosec B603
        command,
        cwd=worktree,
        text=True,
        capture_output=True,
        check=True,
    )


def run_candidate_in_worktree(
    candidate: MutationSweepCandidate,
    index: int,
    candidate_dir: Path,
    worktree: Path,
    request: MutationSweepExecutionRequest,
) -> MutationSweepCandidateResult:
    """Run Mutmut commands inside a prepared worktree."""

    started_at = time.monotonic()
    patch_mutmut_config(worktree / "pyproject.toml", candidate)
    run_result = run_mutmut_step(request, worktree, candidate_dir / "mutmut-run.log", "run")
    stats: mutmut_stats.MutmutStats | None = None
    export_log: Path | None = None
    stats_artifact: Path | None = None
    export_returncode: int | None = None
    error: str | None = None
    if run_result.returncode == 0:
        export_log = candidate_dir / "mutmut-export.log"
        export_result = run_mutmut_step(request, worktree, export_log, "export-cicd-stats")
        export_returncode = export_result.returncode
        if export_result.returncode == 0:
            stats_artifact = candidate_dir / "mutmut-cicd-stats.json"
            stats = collect_stats(worktree / MUTMUT_STATS_PATH, stats_artifact)
        else:
            error = "".join(
                ("mutmut export-cicd-stats exited ", str(export_result.returncode)),
            )
    else:
        error = "".join(("mutmut run exited ", str(run_result.returncode)))
    promotion_ready = is_promotion_ready(
        stats=stats,
        threshold=request.survivor_threshold,
        run_returncode=run_result.returncode,
        export_returncode=export_returncode,
    )
    status = "passed" if error is None and stats is not None else "failed"
    return MutationSweepCandidateResult(
        candidate=candidate,
        index=index,
        status=status,
        duration_seconds=time.monotonic() - started_at,
        run_returncode=run_result.returncode,
        export_returncode=export_returncode,
        promotion_ready=promotion_ready,
        stats=stats,
        run_log=candidate_dir / "mutmut-run.log",
        export_log=export_log,
        stats_path=stats_artifact,
        worktree_path=worktree if request.keep_worktree else None,
        error=error,
    )


def run_mutmut_step(
    request: MutationSweepExecutionRequest,
    worktree: Path,
    log_path: Path,
    step: str,
) -> subprocess.CompletedProcess[str]:
    """Run one Mutmut step inside a worktree."""

    return run_command(
        [*mutmut_command(request), step],
        cwd=worktree,
        env=worktree_env(worktree),
        log_path=log_path,
    )


def run_command(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    log_path: Path,
) -> subprocess.CompletedProcess[str]:
    """Run a command and write raw output to an artifact log."""

    result = subprocess.run(  # nosec B603
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    log_path.write_text(command_log(command, result), encoding="utf-8")
    return result


def collect_stats(stats_path: Path, artifact_path: Path) -> mutmut_stats.MutmutStats:
    """Copy and parse Mutmut stats."""

    stats = mutmut_stats.read_stats(stats_path)
    shutil.copy2(stats_path, artifact_path)
    return stats


def is_promotion_ready(
    *,
    stats: mutmut_stats.MutmutStats | None,
    threshold: int,
    run_returncode: int,
    export_returncode: int | None,
) -> bool:
    """Return whether an advisory candidate is ready for blocking promotion."""

    if stats is None:
        return False
    if run_returncode != 0 or export_returncode != 0:
        return False
    return stats.survived <= threshold and stats.suspicious == 0 and stats.timeout == 0


def command_log(
    command: list[str],
    result: subprocess.CompletedProcess[str],
) -> str:
    """Return raw command log text."""

    return "\n".join(
        (
            " ".join(("$", " ".join(command))),
            "".join(("exit_code=", str(result.returncode))),
            "",
            "## stdout",
            result.stdout,
            "",
            "## stderr",
            result.stderr,
            "",
        ),
    )


def worktree_env(worktree: Path) -> dict[str, str]:
    """Return environment for running Mutmut inside a copied worktree."""

    env = os.environ.copy()
    src_path = str(worktree / "src")
    current_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{src_path}{os.pathsep}{current_pythonpath}" if current_pythonpath else src_path
    )
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def mutmut_command(request: MutationSweepExecutionRequest) -> list[str]:
    """Return Mutmut command prefix."""

    if request.mutmut_command:
        return list(request.mutmut_command)
    resolved_command = shutil.which("mutmut")
    if resolved_command:
        return [resolved_command]
    venv_command = Path(sys.executable).with_name("mutmut")
    if venv_command.exists():
        return [str(venv_command)]
    return ["mutmut"]


def candidate_dir_name(index: int) -> str:
    """Return candidate artifact directory name."""

    return "".join(("candidate-", str(index).zfill(2)))
