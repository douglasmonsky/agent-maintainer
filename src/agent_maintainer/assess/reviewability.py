"""Advisory provider-aware reviewability assessment."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from pathlib import Path

from agent_maintainer.assess.models import (
    ReviewabilityChange,
    ReviewabilityCount,
    ReviewabilityReport,
)
from agent_maintainer.checks.change_budget import FileChange, run_git_numstat
from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.ecosystems.file_changes import ChangedPath, classify_changed_paths
from agent_maintainer.ecosystems.models import FileChangeClassification, FileRole

ADVISORY_NOTE = (
    "Advisory only: current blocking reviewability gates remain Python-backed "
    "until cross-ecosystem policy adapters are proven low-noise."
)

NEXT_COMMANDS = (
    "python -m agent_maintainer verify --profile precommit",
    "python -m agent_maintainer assess reviewability --json",
)

GLOBAL_ROLES = frozenset((FileRole.CONFIG, FileRole.DOCS))


def build_reviewability_report(
    target: Path,
    config: MaintainerConfig,
    *,
    base_ref: str,
    staged: bool,
) -> ReviewabilityReport:
    """Build an advisory changed-file reviewability report."""
    raw_changes = tuple(run_git_numstat(base_ref, staged=staged))
    classifications = classify_changed_paths(
        (ChangedPath(change.path) for change in raw_changes),
        config,
        repo_root=target,
    )
    changes_by_path = {change.path: change for change in raw_changes}
    reviewability_changes = tuple(
        _to_reviewability_change(classification, changes_by_path)
        for classification in classifications
    )
    return ReviewabilityReport(
        target=str(target),
        base_ref=base_ref,
        staged=staged,
        total_changed_files=len(raw_changes),
        classified_files=len(reviewability_changes),
        unclassified_files=len(raw_changes) - len(reviewability_changes),
        by_ecosystem=_counts(change.ecosystem for change in reviewability_changes),
        by_role=_counts(change.role for change in reviewability_changes),
        changes=reviewability_changes,
        advisory_note=ADVISORY_NOTE,
        next_commands=NEXT_COMMANDS,
    )


def _to_reviewability_change(
    classification: FileChangeClassification,
    changes_by_path: dict[str, FileChange],
) -> ReviewabilityChange:
    """Combine provider classification and git numstat details."""
    change = changes_by_path[classification.path]
    return ReviewabilityChange(
        path=classification.path,
        ecosystem=_report_ecosystem(classification),
        role=classification.role.value,
        change_kind=classification.change_kind.value,
        added=change.added,
        deleted=change.deleted,
        generated=classification.generated,
        ignored=classification.ignored,
    )


def _report_ecosystem(classification: FileChangeClassification) -> str:
    """Return report-facing ecosystem label."""
    if classification.role in GLOBAL_ROLES:
        return "global"
    return classification.ecosystem


def _counts(values: Iterable[str]) -> tuple[ReviewabilityCount, ...]:
    """Return deterministic grouped counts."""
    return tuple(
        ReviewabilityCount(key=key, count=count) for key, count in sorted(Counter(values).items())
    )
