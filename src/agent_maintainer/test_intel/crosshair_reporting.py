"""Render advisory CrossHair candidate reports."""

from __future__ import annotations

import json

from agent_maintainer.test_intel.crosshair_candidates import (
    CrosshairCandidate,
    CrosshairCandidateReport,
)


def render_text(report: CrosshairCandidateReport) -> str:
    """Return human-readable advisory CrossHair candidate output."""

    lines = ["CrossHair candidates", ""]
    if report.changed_only:
        lines.extend(render_changed_source(report.changed_source))
    if not report.candidates:
        lines.extend(("- <none>", "", f"Note: {report.note}"))
        return "\n".join(lines).rstrip()
    for index, candidate in enumerate(report.candidates, start=1):
        lines.extend(render_candidate(index, candidate))
    return "\n".join(lines).rstrip()


def render_changed_source(changed_source: tuple[str, ...]) -> list[str]:
    """Return changed-source context lines."""

    lines = ["Changed source:"]
    if changed_source:
        lines.extend(f"- {path}" for path in changed_source)
    else:
        lines.append("- <none>")
    lines.append("")
    return lines


def render_candidate(index: int, candidate: CrosshairCandidate) -> list[str]:
    """Return text lines for one CrossHair candidate."""

    reasons = "; ".join(candidate.reasons)
    return [
        f"{index}. CrossHair candidate: {candidate.path}::{candidate.qualname}",
        f"   Why: {reasons}",
        f"   Suggested command: {candidate.suggested_command}",
        f"   Note: {candidate.note}",
        "",
    ]


def render_json(report: CrosshairCandidateReport) -> str:
    """Return stable JSON candidate output."""

    return json.dumps(report.to_json(), indent=2, sort_keys=True)
