"""Advisory mutation testing target ranking."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.ratchet.baseline import read_baseline
from agent_maintainer.ratchet.ranking import ranked_targets
from agent_maintainer.ratchet.status import status_report
from agent_maintainer.test_intel import hypothesis_candidates

ADVISORY_NOTE = "Advisory only; this command does not run mutmut."
DEFAULT_LIMIT = 10
MIN_SCORE = 4
RATCHET_LIMIT = 50
RATCHET_STATUS_SCORES = (
    ("new", 6),
    ("worsened", 5),
    ("unchanged", 2),
    ("improved", 1),
)


@dataclass(frozen=True)
class MutationTarget:
    """One advisory mutation testing target."""

    path: str
    qualname: str
    score: int
    complexity: int
    reasons: tuple[str, ...]
    suggested_focus: str
    note: str = ADVISORY_NOTE

    def to_json(self) -> dict[str, object]:
        """Return stable JSON payload."""

        return {
            "path": self.path,
            "qualname": self.qualname,
            "score": self.score,
            "complexity": self.complexity,
            "reasons": list(self.reasons),
            "suggested_focus": self.suggested_focus,
            "note": self.note,
        }


@dataclass(frozen=True)
class MutationTargetRequest:
    """Inputs for mutation target report construction."""

    config: MaintainerConfig
    repo_root: Path
    changed_only: bool
    ratchet_enabled: bool
    base_ref: str
    changed_source: tuple[str, ...] = ()
    limit: int = DEFAULT_LIMIT


@dataclass(frozen=True)
class MutationTargetReport:
    """Advisory mutation target report."""

    changed_only: bool
    ratchet_enabled: bool
    changed_source: tuple[str, ...]
    targets: tuple[MutationTarget, ...]
    note: str = ADVISORY_NOTE

    def to_json(self) -> dict[str, object]:
        """Return stable JSON payload."""

        return {
            "changed_only": self.changed_only,
            "ratchet_enabled": self.ratchet_enabled,
            "changed_source": list(self.changed_source),
            "targets": [target.to_json() for target in self.targets],
            "note": self.note,
        }


@dataclass(frozen=True)
class TargetSignals:
    """Mutation target scoring signals."""

    complexity: int
    changed: bool
    likely_test_count: int
    ratchet_score: int


def build_mutation_target_report(request: MutationTargetRequest) -> MutationTargetReport:
    """Return advisory mutation target report."""

    source_paths = (
        request.changed_source
        if request.changed_only
        else hypothesis_candidates.discover_source_files(request.config, request.repo_root)
    )
    changed_set = frozenset(request.changed_source)
    ratchet_scores = (
        ratchet_path_scores(request.config, request.repo_root, request.base_ref, changed_set)
        if request.ratchet_enabled
        else {}
    )
    test_counts = hypothesis_candidates.likely_test_counts(
        source_paths, request.config, request.repo_root
    )
    targets = [
        target
        for source_path in source_paths
        for target in targets_for_source(
            source_path,
            request.repo_root,
            changed=source_path in changed_set,
            likely_test_count=test_counts.get(source_path, 0),
            ratchet_score=ratchet_scores.get(source_path, 0),
        )
    ]
    ranked = tuple(sorted(targets, key=target_sort_key)[: request.limit])
    return MutationTargetReport(
        changed_only=request.changed_only,
        ratchet_enabled=request.ratchet_enabled,
        changed_source=request.changed_source,
        targets=ranked,
    )


def ratchet_path_scores(
    config: MaintainerConfig,
    repo_root: Path,
    base_ref: str,
    changed_paths: frozenset[str],
) -> dict[str, int]:
    """Return ratchet boost scores keyed by source path."""

    baseline_path = repo_root / config.ratchet_baseline_path
    if not baseline_path.exists():
        return {}
    try:
        report = status_report(read_baseline(baseline_path), base_ref=base_ref)
    except (OSError, ValueError, KeyError):
        return {}
    targets = ranked_targets(
        report,
        changed_path_set=set(changed_paths),
        limit=RATCHET_LIMIT,
    )
    return {
        target.path: ratchet_status_score(target.status)
        for target in targets
        if ratchet_status_score(target.status) > 0
    }


def ratchet_status_score(status: str) -> int:
    """Return mutation-test boost score for ratchet status."""

    for status_name, score in RATCHET_STATUS_SCORES:
        if status == status_name:
            return score
    return 0


def targets_for_source(
    source_path: str,
    repo_root: Path,
    *,
    changed: bool,
    likely_test_count: int,
    ratchet_score: int,
) -> tuple[MutationTarget, ...]:
    """Return mutation targets for one source file."""

    source_file = repo_root / source_path
    try:
        tree = hypothesis_candidates.ast.parse(source_file.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return ()
    targets = [
        target
        for function in hypothesis_candidates.iter_public_functions(tree)
        if (
            target := target_for_function(
                source_path,
                function,
                changed=changed,
                likely_test_count=likely_test_count,
                ratchet_score=ratchet_score,
            )
        )
    ]
    return tuple(sorted(targets, key=target_sort_key))


def target_for_function(
    source_path: str,
    function: tuple[str, hypothesis_candidates.ast.FunctionDef],
    *,
    changed: bool,
    likely_test_count: int,
    ratchet_score: int,
) -> MutationTarget | None:
    """Return mutation target when function has enough signals."""

    qualname, node = function
    signals = TargetSignals(
        complexity=hypothesis_candidates.branch_complexity(node),
        changed=changed,
        likely_test_count=likely_test_count,
        ratchet_score=ratchet_score,
    )
    score, reasons = target_score(node, qualname, signals)
    if score < MIN_SCORE:
        return None
    return MutationTarget(
        path=source_path,
        qualname=qualname,
        score=score,
        complexity=signals.complexity,
        reasons=tuple(reasons),
        suggested_focus=mutation_focus(source_path, qualname),
    )


def target_score(
    node: hypothesis_candidates.ast.FunctionDef,
    qualname: str,
    signals: TargetSignals,
) -> tuple[int, list[str]]:
    """Return mutation target score and explanation reasons."""

    score = 0
    reasons: list[str] = []
    if signals.changed:
        score += 4
        reasons.append("changed source")
    if signals.likely_test_count > 0:
        score += 3
        reasons.append("covered by likely focused tests")
    if signals.ratchet_score:
        score += signals.ratchet_score
        reasons.append("critical ratchet target")
    if signals.complexity >= hypothesis_candidates.MIN_BRANCH_COMPLEXITY:
        score += signals.complexity
        reasons.append(f"branch complexity {signals.complexity}")
    if hypothesis_candidates.is_pureish(node):
        score += 2
        reasons.append("pure-ish function")
    if hypothesis_candidates.has_boundary_name(qualname):
        score += 3
        reasons.append("parser/validator/decision logic")
    return score, reasons


def mutation_focus(source_path: str, qualname: str) -> str:
    """Return advisory mutmut focus guidance."""

    return (
        "Run a manual mutmut slice focused on "
        f"{source_path}::{qualname}; do not make mutation testing a precommit gate."
    )


def target_sort_key(target: MutationTarget) -> tuple[int, str, str]:
    """Return deterministic target sort key."""

    return (-target.score, target.path, target.qualname)
