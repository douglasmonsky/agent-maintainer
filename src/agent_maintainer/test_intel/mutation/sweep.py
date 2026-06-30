"""Advisory deep mutation sweep planning."""

from __future__ import annotations

import subprocess  # nosec B404
from dataclasses import dataclass
from pathlib import Path

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.test_intel import coverage, mapping
from agent_maintainer.test_intel.mutation import targets as mutation_targets

ADVISORY_NOTE = "Advisory only; does not run mutmut."
DEFAULT_LIMIT = 5
DEFAULT_TARGET_LIMIT = 3
DEFAULT_TIME_BUDGET_MINUTES = 20
DEFAULT_SURVIVOR_THRESHOLD = 0
MUTMUT_MANUAL_COMMAND = "python -m agent_maintainer verify --profile manual"
CHANGED_SCORE_BONUS = 12
MAX_LIKELY_TEST_SCORE = 12
GroupedMutationTargets = tuple[
    tuple[str, tuple[mutation_targets.MutationTarget, ...]],
    ...,
]


@dataclass(frozen=True)
class MutationSweepRequest:
    """Inputs for advisory mutation sweep planning."""

    config: MaintainerConfig
    repo_root: Path
    base_ref: str
    changed_only: bool
    changed_source: tuple[str, ...] = ()
    limit: int = DEFAULT_LIMIT
    target_limit: int = DEFAULT_TARGET_LIMIT
    time_budget_minutes: int = DEFAULT_TIME_BUDGET_MINUTES
    survivor_threshold: int = DEFAULT_SURVIVOR_THRESHOLD
    stop_when_no_new_findings: bool = True


@dataclass(frozen=True)
class MutationSweepCandidate:
    """One module-level mutation sweep candidate."""

    path: str
    score: int
    target_count: int
    max_complexity: int
    churn: int
    changed: bool
    coverage_percent: float | None
    likely_tests: tuple[str, ...]
    target_qualnames: tuple[str, ...]
    reasons: tuple[str, ...]
    suggested_only_mutate: str
    suggested_command: str = MUTMUT_MANUAL_COMMAND

    def to_json(self) -> dict[str, object]:
        """Return stable JSON payload."""

        return {
            "path": self.path,
            "score": self.score,
            "target_count": self.target_count,
            "max_complexity": self.max_complexity,
            "churn": self.churn,
            "changed": self.changed,
            "coverage_percent": self.coverage_percent,
            "likely_tests": list(self.likely_tests),
            "target_qualnames": list(self.target_qualnames),
            "reasons": list(self.reasons),
            "suggested_only_mutate": self.suggested_only_mutate,
            "suggested_command": self.suggested_command,
        }


@dataclass(frozen=True)
class MutationSweepReport:
    """Advisory mutation sweep report."""

    changed_only: bool
    changed_source: tuple[str, ...]
    candidates: tuple[MutationSweepCandidate, ...]
    stop_conditions: tuple[str, ...]
    note: str = ADVISORY_NOTE

    def to_json(self) -> dict[str, object]:
        """Return stable JSON payload."""

        return {
            "changed_only": self.changed_only,
            "changed_source": list(self.changed_source),
            "candidates": [candidate.to_json() for candidate in self.candidates],
            "stop_conditions": list(self.stop_conditions),
            "note": self.note,
        }


def build_mutation_sweep_report(request: MutationSweepRequest) -> MutationSweepReport:
    """Return advisory deep mutation sweep candidates."""

    target_report = mutation_targets.build_mutation_target_report(
        mutation_targets.MutationTargetRequest(
            config=request.config,
            repo_root=request.repo_root,
            changed_only=request.changed_only,
            ratchet_enabled=True,
            base_ref=request.base_ref,
            changed_source=request.changed_source,
            limit=max(request.limit * request.target_limit * 3, request.limit),
        )
    )
    changed_set = frozenset(request.changed_source)
    candidates = [
        candidate_for_path(
            path,
            targets=targets,
            request=request,
            changed=path in changed_set,
        )
        for path, targets in grouped_targets(target_report.targets)
    ]
    ranked = tuple(sorted(candidates, key=candidate_sort_key)[: request.limit])
    return MutationSweepReport(
        changed_only=request.changed_only,
        changed_source=request.changed_source,
        candidates=ranked,
        stop_conditions=stop_conditions(request),
    )


def grouped_targets(
    targets: tuple[mutation_targets.MutationTarget, ...],
) -> GroupedMutationTargets:
    """Group mutation targets by source path."""

    grouped: dict[str, list[mutation_targets.MutationTarget]] = {}
    for target in targets:
        grouped.setdefault(target.path, []).append(target)
    return tuple((path, tuple(items)) for path, items in sorted(grouped.items()))


def candidate_for_path(
    path: str,
    *,
    targets: tuple[mutation_targets.MutationTarget, ...],
    request: MutationSweepRequest,
    changed: bool,
) -> MutationSweepCandidate:
    """Return sweep candidate for one source path."""

    likely_tests = likely_test_paths(path, request.config, request.repo_root)
    coverage_percent = source_coverage_percent(request.repo_root, path)
    churn = git_churn_count(request.repo_root, path)
    score, reasons = candidate_score(
        targets=targets,
        changed=changed,
        likely_tests=likely_tests,
        coverage_percent=coverage_percent,
        churn=churn,
    )
    return MutationSweepCandidate(
        path=path,
        score=score,
        target_count=len(targets),
        max_complexity=max(target.complexity for target in targets),
        churn=churn,
        changed=changed,
        coverage_percent=coverage_percent,
        likely_tests=likely_tests,
        target_qualnames=tuple(target.qualname for target in targets[: request.target_limit]),
        reasons=tuple(reasons),
        suggested_only_mutate=path,
    )


def candidate_score(
    *,
    targets: tuple[mutation_targets.MutationTarget, ...],
    changed: bool,
    likely_tests: tuple[str, ...],
    coverage_percent: float | None,
    churn: int,
) -> tuple[int, list[str]]:
    """Return sweep score and explanation."""

    score = max(target.score for target in targets)
    reasons = [f"{len(targets)} mutation target(s)"]
    if changed:
        score += CHANGED_SCORE_BONUS
        reasons.append("changed source")
    if likely_tests:
        score += min(len(likely_tests) * 4, MAX_LIKELY_TEST_SCORE)
        reasons.append(f"{len(likely_tests)} likely focused test(s)")
    if coverage_percent is not None:
        score += int(min(coverage_percent, 100.0) // 10)
        reasons.append(f"{coverage_percent:.1f}% file coverage")
    if churn:
        score += min(churn, 10)
        reasons.append(f"{churn} recent commit(s) touched this file")
    reasons.extend(unique_target_reasons(targets))
    return score, reasons


def unique_target_reasons(
    targets: tuple[mutation_targets.MutationTarget, ...],
) -> tuple[str, ...]:
    """Return stable unique target reasons."""

    reasons: list[str] = []
    for target in targets:
        for reason in target.reasons:
            if reason not in reasons:
                reasons.append(reason)
    return tuple(reasons)


def likely_test_paths(
    path: str,
    config: MaintainerConfig,
    repo_root: Path,
) -> tuple[str, ...]:
    """Return likely focused tests for one source path."""

    matches = mapping.likely_tests_for_changes((path,), config, repo_root)
    return tuple(match.test_path for match in matches)


def source_coverage_percent(repo_root: Path, path: str) -> float | None:
    """Return file coverage percent if coverage artifacts exist."""

    summary = coverage.coverage_from_json(repo_root / "coverage.json", (path,))
    return summary.changed_source_file_coverage


def git_churn_count(repo_root: Path, path: str) -> int:
    """Return recent commit count touching a source path."""

    try:
        result = subprocess.run(  # nosec B603
            ("git", "log", "--since=180 days ago", "--format=%H", "--", path),
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return 0
    return len({line for line in result.stdout.splitlines() if line})


def stop_conditions(request: MutationSweepRequest) -> tuple[str, ...]:
    """Return configured advisory sweep stop conditions."""

    conditions = [
        f"time budget {request.time_budget_minutes} minute(s)",
        f"target limit {request.target_limit} function(s) per file",
        f"survivor threshold {request.survivor_threshold}",
    ]
    if request.stop_when_no_new_findings:
        conditions.append("stop when no new findings appear")
    return tuple(conditions)


def candidate_sort_key(candidate: MutationSweepCandidate) -> tuple[int, str]:
    """Return deterministic candidate sort key."""

    return (-candidate.score, candidate.path)
