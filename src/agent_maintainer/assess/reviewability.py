"""Advisory provider-aware reviewability assessment."""

from __future__ import annotations

import subprocess  # nosec B404
from collections import Counter
from collections.abc import Iterable
from pathlib import Path

from agent_maintainer.assess import models as assess_models
from agent_maintainer.checks import suppression_budget
from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.ecosystems import file_changes, git_changes
from agent_maintainer.ecosystems import models as ecosystem_models
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
SOURCE_TEST_ADVISORY_ECOSYSTEMS = frozenset(("typescript",))
SOURCE_HEAVY_FILE_LIMIT = 4
SOURCE_HEAVY_LINE_LIMIT = 200


def build_reviewability_report(
    target: Path,
    config: MaintainerConfig,
    *,
    base_ref: str,
    staged: bool,
) -> assess_models.ReviewabilityReport:
    """Build advisory changed-file reviewability report."""
    raw_changes = tuple(git_changes.run_git_numstat(base_ref, staged=staged))
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
    summaries = _provider_summaries(reviewability_changes, suppression_findings)
    return assess_models.ReviewabilityReport(
        target=str(target),
        base_ref=base_ref,
        staged=staged,
        total_changed_files=len(raw_changes),
        classified_files=len(reviewability_changes),
        unclassified_files=len(raw_changes) - len(reviewability_changes),
        by_ecosystem=_counts(change.ecosystem for change in reviewability_changes),
        by_role=_counts(change.role for change in reviewability_changes),
        provider_summaries=summaries,
        advisory_findings=_advisory_findings(summaries),
        changes=reviewability_changes,
        suppressions=suppression_findings,
        broad_suppressions=sum(1 for finding in suppression_findings if finding.broad),
        advisory_note=ADVISORY_NOTE,
        next_commands=NEXT_COMMANDS,
    )


def added_lines_by_path(base_ref: str, *, staged: bool) -> dict[str, tuple[str, ...]]:
    """Return added diff lines grouped by destination path."""
    copied_paths = suppression_budget.copied_destination_paths(base_ref, staged=staged)
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
        raise RuntimeError(f"Could not calculate diff lines for {target}: {stderr}") from exc
    return _parse_added_lines(result.stdout, copied_paths)


def _parse_added_lines(
    patch_text: str,
    copied_paths: frozenset[str],
) -> dict[str, tuple[str, ...]]:
    """Parse added lines from unified diff output."""
    grouped: dict[str, list[str]] = {}
    current_path: str | None = None
    for line in patch_text.splitlines():
        if line.startswith("+++ "):
            path = line.removeprefix("+++ ").removeprefix("b/")
            current_path = None if path == "/dev/null" or path in copied_paths else path
            continue
        if current_path and line.startswith("+") and not line.startswith("+++"):
            grouped.setdefault(current_path, []).append(line[1:])
    return {path: tuple(lines) for path, lines in grouped.items()}


def _to_reviewability_change(
    classification: ecosystem_models.FileChangeClassification,
    changes_by_path: dict[str, git_changes.FileChange],
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
    return ()


def _provider_summaries(
    changes: tuple[assess_models.ReviewabilityChange, ...],
    suppressions: tuple[assess_models.ReviewabilitySuppression, ...],
) -> tuple[assess_models.ReviewabilityProviderSummary, ...]:
    """Return source/test reviewability summaries per provider."""
    visible_changes = tuple(
        change
        for change in changes
        if change.ecosystem != "global" and not change.generated and not change.ignored
    )
    broad_counts = Counter(finding.ecosystem for finding in suppressions if finding.broad)
    return tuple(
        _provider_summary(ecosystem, visible_changes, broad_counts)
        for ecosystem in sorted({change.ecosystem for change in visible_changes})
    )


def _provider_summary(
    ecosystem: str,
    changes: tuple[assess_models.ReviewabilityChange, ...],
    broad_counts: Counter[str],
) -> assess_models.ReviewabilityProviderSummary:
    """Return one provider advisory source/test summary."""
    provider_changes = tuple(change for change in changes if change.ecosystem == ecosystem)
    source_changes = tuple(change for change in provider_changes if change.role == "source")
    test_changes = tuple(change for change in provider_changes if change.role == "test")
    return assess_models.ReviewabilityProviderSummary(
        ecosystem=ecosystem,
        changed_files=len(provider_changes),
        source_files=len(source_changes),
        test_files=len(test_changes),
        source_lines=sum(_changed_lines(change) for change in source_changes),
        test_lines=sum(_changed_lines(change) for change in test_changes),
        broad_suppressions=broad_counts[ecosystem],
    )


def _advisory_findings(
    summaries: tuple[assess_models.ReviewabilityProviderSummary, ...],
) -> tuple[assess_models.ReviewabilityFinding, ...]:
    """Return non-blocking provider reviewability findings."""
    findings: list[assess_models.ReviewabilityFinding] = []
    for summary in summaries:
        findings.extend(_broad_suppression_findings(summary))
        if summary.ecosystem in SOURCE_TEST_ADVISORY_ECOSYSTEMS:
            findings.extend(_source_without_test_findings(summary))
            findings.extend(_source_heavy_findings(summary))
    return tuple(findings)


def _broad_suppression_findings(
    summary: assess_models.ReviewabilityProviderSummary,
) -> tuple[assess_models.ReviewabilityFinding, ...]:
    """Return broad suppression finding for one provider summary."""
    if summary.broad_suppressions == 0:
        return ()
    return (
        assess_models.ReviewabilityFinding(
            ecosystem=summary.ecosystem,
            kind="broad-suppression",
            message=f"{summary.broad_suppressions} broad advisory suppression(s).",
            recommendation="Prefer narrow suppressions or remove the suppression.",
        ),
    )


def _source_without_test_findings(
    summary: assess_models.ReviewabilityProviderSummary,
) -> tuple[assess_models.ReviewabilityFinding, ...]:
    """Return source-without-test finding for one provider summary."""
    if summary.source_files == 0 or summary.test_files > 0:
        return ()
    return (
        assess_models.ReviewabilityFinding(
            ecosystem=summary.ecosystem,
            kind="source-without-test",
            message=f"{summary.source_files} source file(s) changed without tests.",
            recommendation="Add or update relevant tests if behavior changed.",
        ),
    )


def _source_heavy_findings(
    summary: assess_models.ReviewabilityProviderSummary,
) -> tuple[assess_models.ReviewabilityFinding, ...]:
    """Return source-heavy finding for one provider summary."""
    if (
        summary.source_files < SOURCE_HEAVY_FILE_LIMIT
        and summary.source_lines < SOURCE_HEAVY_LINE_LIMIT
    ):
        return ()
    return (
        assess_models.ReviewabilityFinding(
            ecosystem=summary.ecosystem,
            kind="source-heavy",
            message=(
                f"{summary.source_files} source file(s), "
                f"{summary.source_lines} source line(s) changed."
            ),
            recommendation="Consider splitting the change or adding a change plan.",
        ),
    )


def _changed_lines(change: assess_models.ReviewabilityChange) -> int:
    """Return total changed lines for one reviewability change."""
    return change.added + change.deleted


def _counts(values: Iterable[str]) -> tuple[assess_models.ReviewabilityCount, ...]:
    """Return deterministic grouped counts."""
    return tuple(
        assess_models.ReviewabilityCount(key=key, count=count)
        for key, count in sorted(Counter(values).items())
    )
