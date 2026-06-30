"""Data models for advisory mutation sweep execution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from agent_maintainer.runners import mutmut_stats
from agent_maintainer.test_intel.mutation_sweep import MutationSweepCandidate

DEFAULT_OUTPUT_DIR: Final = Path(".verify-logs/mutation-sweeps")
DEFAULT_EXECUTION_CANDIDATE_LIMIT: Final = 1


@dataclass(frozen=True)
class MutationSweepExecutionRequest:
    """Inputs for advisory mutation sweep execution."""

    repo_root: Path
    output_dir: Path = DEFAULT_OUTPUT_DIR
    candidate_limit: int = DEFAULT_EXECUTION_CANDIDATE_LIMIT
    time_budget_minutes: int = 20
    survivor_threshold: int = 0
    keep_worktree: bool = False
    fail_fast: bool = False
    mutmut_command: tuple[str, ...] = ()


@dataclass(frozen=True)
class MutationSweepCandidateResult:
    """Executed mutation sweep result for one candidate."""

    candidate: MutationSweepCandidate
    index: int
    status: str
    duration_seconds: float
    run_returncode: int
    export_returncode: int | None
    promotion_ready: bool
    stats: mutmut_stats.MutmutStats | None
    run_log: Path
    export_log: Path | None
    stats_path: Path | None
    worktree_path: Path | None
    error: str | None = None

    @property
    def failed(self) -> bool:
        """Return whether executor or runner failed for this candidate."""

        return self.status == "failed"

    def to_json(self, artifact_dir: Path) -> dict[str, object]:
        """Return stable JSON payload."""

        return {
            "candidate": self.candidate.to_json(),
            "index": self.index,
            "status": self.status,
            "duration_seconds": round(self.duration_seconds, 3),
            "run_returncode": self.run_returncode,
            "export_returncode": self.export_returncode,
            "promotion_ready": self.promotion_ready,
            "stats": stats_to_json(self.stats),
            "run_log": relative_artifact(self.run_log, artifact_dir),
            "export_log": relative_artifact(self.export_log, artifact_dir),
            "stats_path": relative_artifact(self.stats_path, artifact_dir),
            "worktree_path": path_to_string(self.worktree_path),
            "error": self.error,
        }


@dataclass(frozen=True)
class MutationSweepExecutionReport:
    """Artifact-backed mutation sweep execution report."""

    run_id: str
    artifact_dir: Path
    results: tuple[MutationSweepCandidateResult, ...]
    stopped_reason: str | None = None

    @property
    def has_failures(self) -> bool:
        """Return whether any executor or runner failure occurred."""

        return any(result.failed for result in self.results)

    def to_json(self) -> dict[str, object]:
        """Return stable JSON payload."""

        return {
            "run_id": self.run_id,
            "artifact_dir": str(self.artifact_dir),
            "stopped_reason": self.stopped_reason,
            "has_failures": self.has_failures,
            "results": [result.to_json(self.artifact_dir) for result in self.results],
        }


def stats_to_json(stats: mutmut_stats.MutmutStats | None) -> dict[str, object] | None:
    """Return JSON stats mapping."""

    if stats is None:
        return None
    return {
        "killed": stats.killed,
        "survived": stats.survived,
        "total": stats.total,
        "no_tests": stats.no_tests,
        "skipped": stats.skipped,
        "suspicious": stats.suspicious,
        "timeout": stats.timeout,
        "score": round(stats.score, 3),
    }


def relative_artifact(path: Path | None, artifact_dir: Path) -> str | None:
    """Return artifact-relative path when available."""

    if path is None:
        return None
    try:
        return str(path.relative_to(artifact_dir))
    except ValueError:
        return str(path)


def path_to_string(path: Path | None) -> str | None:
    """Return string path or none."""

    if path is not None:
        return str(path)
    return None
