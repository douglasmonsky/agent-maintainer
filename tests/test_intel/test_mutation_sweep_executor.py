"""Tests advisory mutation sweep execution."""

from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

import pytest

from agent_maintainer.runners import mutmut_stats
from agent_maintainer.test_intel.mutation import sweep as mutation_sweep
from agent_maintainer.test_intel.mutation import sweep_execution as mutation_sweep_execution
from agent_maintainer.test_intel.mutation import sweep_executor as mutation_sweep_executor
from agent_maintainer.test_intel.mutation import sweep_reporting as mutation_sweep_reporting
from agent_maintainer.test_intel.mutation import sweep_runner as mutation_sweep_runner
from tests.support.callbacks import constant_callback

EXECUTABLE_MODE = 0o755
FAKE_KILLED_MUTANTS = 4
FAKE_TOTAL_MUTANTS = 4
READY_SURVIVORS = 2
CANDIDATE_SCORE = 31
CANDIDATE_COVERAGE = 95.0


# docsync:evidence.start evidence.mutation_testing.sweep_executor_tests
def test_executor_keeps_repo_config(tmp_path: Path) -> None:
    """Executor patches copied pyproject, not source checkout config."""

    repo_root, original_pyproject, report = run_successful_execution(tmp_path)
    result = report.results[0]

    assert repo_root.joinpath("pyproject.toml").read_text(encoding="utf-8") == original_pyproject
    assert result.worktree_path is not None
    assert result.worktree_path.joinpath(".git").exists()
    patched_pyproject = result.worktree_path.joinpath("pyproject.toml").read_text(
        encoding="utf-8",
    )
    assert '"src/pkg/logic.py"' in patched_pyproject
    assert '"src/pkg/old.py"' not in patched_pyproject


def test_executor_writes_artifacts(tmp_path: Path) -> None:
    """Executor captures raw logs and writes run artifacts."""

    _repo_root, _original_pyproject, report = run_successful_execution(tmp_path)
    result = report.results[0]

    assert "RAW MUTMUT PROGRESS" in result.run_log.read_text(encoding="utf-8")
    assert "RAW MUTMUT PROGRESS" not in mutation_sweep_reporting.render_execution_text(report)
    assert report.artifact_dir.joinpath("manifest.json").exists()
    assert report.artifact_dir.joinpath("summary.md").exists()


def test_executor_reports_success_stats(tmp_path: Path) -> None:
    """Executor parses Mutmut stats and marks ready candidates."""

    _repo_root, _original_pyproject, report = run_successful_execution(tmp_path)
    result = report.results[0]

    assert not report.has_failures
    assert result.promotion_ready is True
    assert result.stats is not None
    assert result.stats.survived == 0


# docsync:evidence.end evidence.mutation_testing.sweep_executor_tests


def test_executor_candidate_limit(tmp_path: Path) -> None:
    """Executor runs only requested number ranked candidates."""

    repo_root = write_mutmut_repo(tmp_path / "repo")
    fake_mutmut = write_fake_mutmut(tmp_path / "fake_mutmut.py")
    first_candidate = candidate(path="src/pkg/logic.py")
    second_candidate = candidate(path="src/pkg/other.py")

    report = mutation_sweep_executor.execute_mutation_sweep(
        report_for_candidates((first_candidate, second_candidate)),
        mutation_sweep_execution.MutationSweepExecutionRequest(
            repo_root=repo_root,
            output_dir=tmp_path / "logs",
            candidate_limit=1,
            mutmut_command=(sys.executable, str(fake_mutmut)),
        ),
    )

    assert len(report.results) == 1
    assert report.results[0].candidate.path == "src/pkg/logic.py"


def test_executor_time_budget(tmp_path: Path) -> None:
    """Executor does not start after exhausted time budget."""

    repo_root = write_mutmut_repo(tmp_path / "repo")
    fake_mutmut = write_fake_mutmut(tmp_path / "fake_mutmut.py")

    report = mutation_sweep_executor.execute_mutation_sweep(
        report_for_candidates((candidate(),)),
        mutation_sweep_execution.MutationSweepExecutionRequest(
            repo_root=repo_root,
            output_dir=tmp_path / "logs",
            time_budget_minutes=0,
            mutmut_command=(sys.executable, str(fake_mutmut)),
        ),
    )

    assert report.results == ()
    assert report.stopped_reason == "time budget exhausted"


def test_executor_fail_fast(tmp_path: Path) -> None:
    """Executor stops after first runner failure when fail-fast is enabled."""

    repo_root = write_mutmut_repo(tmp_path / "repo")
    fake_mutmut = write_fake_mutmut(tmp_path / "fake_mutmut.py", run_exit=7)

    report = mutation_sweep_executor.execute_mutation_sweep(
        report_for_candidates(
            (candidate(path="src/pkg/logic.py"), candidate(path="src/pkg/other.py")),
        ),
        mutation_sweep_execution.MutationSweepExecutionRequest(
            repo_root=repo_root,
            output_dir=tmp_path / "logs",
            candidate_limit=2,
            fail_fast=True,
            mutmut_command=(sys.executable, str(fake_mutmut)),
        ),
    )

    assert report.has_failures
    assert len(report.results) == 1
    assert report.results[0].status == "failed"
    assert report.results[0].export_log is None
    assert report.stopped_reason == "fail-fast after src/pkg/logic.py"


def test_promotion_ready_requires_stable_stats() -> None:
    """Promotion readiness requires survivor threshold and stable outcomes."""

    clean_stats = stats(survived=READY_SURVIVORS, suspicious=0, timeout=0)
    suspicious_stats = stats(survived=0, suspicious=1, timeout=0)

    assert mutation_sweep_runner.is_promotion_ready(
        stats=clean_stats,
        threshold=READY_SURVIVORS,
        run_returncode=0,
        export_returncode=0,
    )
    assert not mutation_sweep_runner.is_promotion_ready(
        stats=clean_stats,
        threshold=1,
        run_returncode=0,
        export_returncode=0,
    )
    assert not mutation_sweep_runner.is_promotion_ready(
        stats=suspicious_stats,
        threshold=READY_SURVIVORS,
        run_returncode=0,
        export_returncode=0,
    )


def test_mutmut_command_uses_venv_script(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mutmut resolution falls back to current interpreter sibling."""

    bin_dir = tmp_path / "venv" / "bin"
    bin_dir.mkdir(parents=True)
    python_path = bin_dir / "python"
    mutmut_path = bin_dir / "mutmut"
    python_path.write_text("", encoding="utf-8")
    mutmut_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(mutation_sweep_runner.shutil, "which", constant_callback(None))
    monkeypatch.setattr(sys, "executable", str(python_path))

    command = mutation_sweep_runner.mutmut_command(
        mutation_sweep_execution.MutationSweepExecutionRequest(repo_root=tmp_path),
    )

    assert command == [str(mutmut_path)]


def run_successful_execution(
    tmp_path: Path,
) -> tuple[Path, str, mutation_sweep_execution.MutationSweepExecutionReport]:
    """Run fake successful mutation sweep and return source config."""

    repo_root = write_mutmut_repo(tmp_path / "repo")
    original_pyproject = repo_root.joinpath("pyproject.toml").read_text(encoding="utf-8")
    fake_mutmut = write_fake_mutmut(tmp_path / "fake_mutmut.py")
    report = mutation_sweep_executor.execute_mutation_sweep(
        report_for_candidates((candidate(),)),
        mutation_sweep_execution.MutationSweepExecutionRequest(
            repo_root=repo_root,
            output_dir=tmp_path / "logs",
            keep_worktree=True,
            mutmut_command=(sys.executable, str(fake_mutmut)),
        ),
    )
    return repo_root, original_pyproject, report


def report_for_candidates(
    candidates: tuple[mutation_sweep.MutationSweepCandidate, ...],
) -> mutation_sweep.MutationSweepReport:
    """Return minimal sweep report for execution tests."""

    return mutation_sweep.MutationSweepReport(
        changed_only=False,
        changed_source=(),
        candidates=candidates,
        stop_conditions=("time budget 20 minute(s)",),
    )


def candidate(
    *,
    path: str = "src/pkg/logic.py",
    likely_tests: tuple[str, ...] = ("tests/test_logic.py",),
) -> mutation_sweep.MutationSweepCandidate:
    """Return a mutation sweep candidate."""

    return mutation_sweep.MutationSweepCandidate(
        path=path,
        score=CANDIDATE_SCORE,
        target_count=2,
        max_complexity=3,
        churn=1,
        changed=False,
        coverage_percent=CANDIDATE_COVERAGE,
        likely_tests=likely_tests,
        target_qualnames=("pkg.logic.branch",),
        reasons=("branchy logic",),
        suggested_only_mutate=path,
    )


def stats(
    *,
    survived: int,
    suspicious: int,
    timeout: int,
) -> mutmut_stats.MutmutStats:
    """Return Mutmut stats for readiness checks."""

    return mutmut_stats.MutmutStats(
        killed=10,
        survived=survived,
        total=10 + survived,
        no_tests=0,
        skipped=0,
        suspicious=suspicious,
        timeout=timeout,
        check_was_interrupted_by_user=0,
        segfault=0,
    )


def write_mutmut_repo(path: Path) -> Path:
    """Write minimal repo with Mutmut configuration."""

    path.joinpath("src/pkg").mkdir(parents=True)
    path.joinpath("tests").mkdir()
    path.joinpath("src/pkg/logic.py").write_text("def branch(value):\n    return value\n")
    path.joinpath("tests/test_logic.py").write_text("def test_branch():\n    assert True\n")
    path.joinpath("pyproject.toml").write_text(
        textwrap.dedent(
            """
            [tool.mutmut]
            source_paths = ["src/pkg"]
            only_mutate = [
              "src/pkg/old.py",
            ]
            pytest_add_cli_args_test_selection = [
              "tests/test_old.py",
            ]
            pytest_add_cli_args = ["-q"]
            mutate_only_covered_lines = true
            """,
        ).lstrip(),
        encoding="utf-8",
    )
    return path


def write_fake_mutmut(path: Path, *, run_exit: int = 0) -> Path:
    """Write fake Mutmut command for execution tests."""

    path.write_text(fake_mutmut_source(run_exit), encoding="utf-8")
    path.chmod(EXECUTABLE_MODE)
    return path


def fake_mutmut_source(run_exit: int) -> str:
    """Return fake Mutmut command source."""

    stats_payload = {
        "killed": FAKE_KILLED_MUTANTS,
        "survived": 0,
        "total": FAKE_TOTAL_MUTANTS,
        "no_tests": 0,
        "skipped": 0,
        "suspicious": 0,
        "timeout": 0,
        "check_was_interrupted_by_user": 0,
        "segfault": 0,
    }
    return textwrap.dedent(
        f"""
        from pathlib import Path
        import json
        import sys

        if sys.argv[-1] == "run":
            print("RAW MUTMUT PROGRESS")
            raise SystemExit({run_exit})
        if sys.argv[-1] == "export-cicd-stats":
            Path("mutants").mkdir(exist_ok=True)
            Path("mutants/mutmut-cicd-stats.json").write_text(
                json.dumps({json.dumps(stats_payload)}),
                encoding="utf-8",
            )
            print("RAW EXPORT PROGRESS")
            raise SystemExit(0)
        raise SystemExit(2)
        """,
    ).lstrip()
