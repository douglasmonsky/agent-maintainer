"""Advisory provider-aware reviewability assessment."""

from __future__ import annotations

import subprocess  # nosec B404
from collections import Counter
from collections.abc import Iterable
from pathlib import Path

from agent_maintainer.assess import models as assess_models
from agent_maintainer.checks import change_budget, suppression_budget
from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.ecosystems import file_changes
from agent_maintainer.ecosystems import models as ecosystem_models
from agent_maintainer.ecosystems.go import suppressions as go_suppressions
from agent_maintainer.ecosystems.typescript import suppressions as ts_suppressions

ADVISORY_NOTE = (
    "Advisory only: current blocking reviewability gates remain Python-backed "
    "until cross-ecosystem policy adapters are proven low-noise."
)

NEXT_COMMANDS = (
    "python -m agent_maintainer verify --profile precommit",
    "python -m agent_maintainer assess reviewability --json",
)

GLOBAL_ROLES = frozenset(
    (ecosystem_models.FileRole.CONFIG, ecosystem_models.FileRole.DOCS),
)


def build_reviewability_report(
    target: Path,
    config: MaintainerConfig,
    *,
    base_ref: str,
    staged: bool,
) -> assess_models.ReviewabilityReport:
    """Build advisory changed-file reviewability report."""
    raw_changes = tuple(change_budget.run_git_numstat(base_ref, staged=staged))
    classifications = file_changes.classify_changed_paths(
        (file_changes.ChangedPath(change.path) for change in raw_changes),
        config,
        repo_root=target,
    )
    changes_by_path = {change.path: change for change in raw_changes}
    added_lines = added_lines_by_path(base_ref, staged=staged)
    reviewability_changes = tuple(
        _to_reviewability_change(classification, changes_by_path)
        for classification in classifications
    )
    suppression_findings = tuple(
        finding
        for classification in classifications
        for finding in _suppression_findings(classification, added_lines)
    )

    return assess_models.ReviewabilityReport(
        target=str(target),
        base_ref=base_ref,
        staged=staged,
        total_changed_files=len(raw_changes),
        classified_files=len(reviewability_changes),
        unclassified_files=len(raw_changes) - len(reviewability_changes),
        by_ecosystem=_counts(change.ecosystem for change in reviewability_changes),
        by_role=_counts(change.role for change in reviewability_changes),
        changes=reviewability_changes,
        suppressions=suppression_findings,
        broad_suppressions=sum(1 for finding in suppression_findings if finding.broad),
        advisory_note=ADVISORY_NOTE,
        next_commands=NEXT_COMMANDS,
    )


def added_lines_by_path(base_ref: str, *, staged: bool) -> dict[str, tuple[str, ...]]:
    """Return added patch lines grouped by changed path."""
    try:
        result = subprocess.run(  # nosec B603
            suppression_budget.git_diff_command(base_ref, staged=staged),
            text=True,
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else "unknown git diff failure"
        target = suppression_budget.diff_target_label(base_ref, staged=staged)
        raise RuntimeError(
            f"Could not calculate reviewability diff {target}: {stderr}",
        ) from exc
    copied_destinations = suppression_budget.copied_destination_paths(
        base_ref,
        staged=staged,
    )
    return _parse_added_lines(result.stdout, copied_destinations=copied_destinations)


def _parse_added_lines(
    diff_stdout: str,
    *,
    copied_destinations: frozenset[str],
) -> dict[str, tuple[str, ...]]:
    """Parse added patch lines by path."""
    grouped: dict[str, list[str]] = {}
    current_path = ""
    for line in diff_stdout.splitlines():
        if line.startswith("+++ b/"):
            current_path = line.removeprefix("+++ b/")
            continue
        if current_path in copied_destinations:
            continue
        if line.startswith("+") and not line.startswith("+++"):
            grouped.setdefault(current_path, []).append(line[1:])
    return {path: tuple(lines) for path, lines in grouped.items()}


def _to_reviewability_change(
    classification: ecosystem_models.FileChangeClassification,
    changes_by_path: dict[str, change_budget.FileChange],
) -> assess_models.ReviewabilityChange:
    """Combine provider classification and git numstat details."""
    change = changes_by_path[classification.path]
    return assess_models.ReviewabilityChange(
        path=classification.path,
        ecosystem=_report_ecosystem(classification),
        role=classification.role.value,
        change_kind=classification.change_kind.value,
        added=change.added,
        deleted=change.deleted,
        generated=classification.generated,
        ignored=classification.ignored,
    )


def _report_ecosystem(
    classification: ecosystem_models.FileChangeClassification,
) -> str:
    """Return report-facing ecosystem label."""
    if classification.role in GLOBAL_ROLES:
        return "global"
    return classification.ecosystem


def _suppression_findings(
    classification: ecosystem_models.FileChangeClassification,
    added_lines: dict[str, tuple[str, ...]],
) -> tuple[assess_models.ReviewabilitySuppression, ...]:
    """Return advisory suppression findings for one changed file."""
    if classification.generated or classification.ignored:
        return ()
    findings = tuple(
        finding
        for line in added_lines.get(classification.path, ())
        for finding in _classify_suppression_line(classification.ecosystem, line)
    )
    return tuple(
        assess_models.ReviewabilitySuppression(
            path=classification.path,
            ecosystem=finding.ecosystem,
            kind=finding.kind,
            broad=finding.broad,
            reason=finding.reason,
        )
        for finding in findings
    )


def _classify_suppression_line(
    ecosystem: str,
    line: str,
) -> tuple[ecosystem_models.SuppressionFinding, ...]:
    """Dispatch line-level suppression classification by ecosystem."""
    if ecosystem == "typescript":
        return ts_suppressions.classify_line(line)
    if ecosystem == "go":
        return go_suppressions.classify_line(line)
    return ()


def _counts(values: Iterable[str]) -> tuple[assess_models.ReviewabilityCount, ...]:
    """Return deterministic grouped counts."""
    return tuple(
        assess_models.ReviewabilityCount(key=key, count=count)
        for key, count in sorted(Counter(values).items())
    )
