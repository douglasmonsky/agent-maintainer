"""Compare current findings with a ratchet baseline."""

from __future__ import annotations

from pathlib import Path

from agent_maintainer.ratchet.findings import current_findings
from agent_maintainer.ratchet.models import (
    RatchetBaseline,
    RatchetFinding,
    RatchetStatusEntry,
    RatchetStatusReport,
)

NumericValue = int | float
NUMERIC_TYPES = (int, float)


def status_report(
    baseline: RatchetBaseline,
    *,
    base_ref: str,
) -> RatchetStatusReport:
    """Return ratchet status compared with the current repository."""

    current = current_findings(baseline.provenance.checks)
    entries = compare_findings(baseline.findings, current)
    return RatchetStatusReport(
        entries=entries,
        stale_reasons=stale_reasons(baseline, current, base_ref),
    )


def compare_findings(
    baseline: tuple[RatchetFinding, ...],
    current: tuple[RatchetFinding, ...],
) -> tuple[RatchetStatusEntry, ...]:
    """Compare baseline and current findings."""

    baseline_map = {finding.fingerprint: finding for finding in baseline}
    current_map = {finding.fingerprint: finding for finding in current}
    entries: list[RatchetStatusEntry] = []
    for fingerprint in sorted(current_map):
        active = current_map[fingerprint]
        previous = baseline_map.get(fingerprint)
        entries.append(RatchetStatusEntry(status_for(previous, active), active, previous))
    entries.extend(resolved_entries(baseline_map, current_map))
    return tuple(entries)


def status_for(
    previous: RatchetFinding | None,
    active: RatchetFinding,
) -> str:
    """Return status category for one active finding."""

    if previous is None:
        return "new"
    pair = numeric_pair(previous.value, active.value)
    if pair is None:
        return "unchanged"
    previous_value, active_value = pair
    if active_value > previous_value:
        return "worsened"
    if active_value < previous_value:
        return "improved"
    return "unchanged"


def resolved_entries(
    baseline_map: dict[str, RatchetFinding],
    current_map: dict[str, RatchetFinding],
) -> tuple[RatchetStatusEntry, ...]:
    """Return entries for findings present only in baseline."""

    return tuple(
        RatchetStatusEntry(status="resolved", finding=finding, baseline=finding)
        for fingerprint, finding in sorted(baseline_map.items())
        if fingerprint not in current_map
    )


def stale_reasons(
    baseline: RatchetBaseline,
    current: tuple[RatchetFinding, ...],
    base_ref: str,
) -> tuple[str, ...]:
    """Return reasons a baseline needs review."""

    reasons: list[str] = []
    if baseline.provenance.dirty_state:
        reasons.append("baseline was created from a dirty worktree")
    if baseline.provenance.base_ref != base_ref:
        expected = repr(baseline.provenance.base_ref)
        actual = repr(base_ref)
        reasons.append(f"baseline base ref {expected} differs from {actual}")
    reasons.extend(deleted_file_reasons(baseline.findings))
    reasons.extend(missing_current_reasons(baseline.findings, current))
    return tuple(reasons)


def deleted_file_reasons(findings: tuple[RatchetFinding, ...]) -> tuple[str, ...]:
    """Return stale reasons for baseline paths no longer present."""

    paths = sorted({finding.path for finding in findings if finding.path})
    return tuple(
        f"baseline path no longer exists: {path}" for path in paths if not Path(path).exists()
    )


def missing_current_reasons(
    baseline: tuple[RatchetFinding, ...],
    current: tuple[RatchetFinding, ...],
) -> tuple[str, ...]:
    """Return stale reasons for baseline findings no longer current."""

    current_fingerprints = {finding.fingerprint for finding in current}
    return tuple(
        f"baseline finding is no longer current: {finding.identity}"
        for finding in baseline
        if finding.fingerprint not in current_fingerprints
    )


def numeric_pair(left: object, right: object) -> tuple[NumericValue, NumericValue] | None:
    """Return values as comparable numbers when possible."""

    if isinstance(left, NUMERIC_TYPES) and isinstance(right, NUMERIC_TYPES):
        return left, right
    return None
