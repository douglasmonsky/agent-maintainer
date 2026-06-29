"""Render advisory Hypothesis candidate reports."""

from __future__ import annotations

import json

from agent_maintainer.test_intel.hypothesis_candidates import (
    HypothesisCandidate,
    HypothesisCandidateReport,
)


def render_text(report: HypothesisCandidateReport) -> str:
    """Return human-readable advisory candidate output."""

    lines = ["Hypothesis candidates", ""]
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


def render_candidate(index: int, candidate: HypothesisCandidate) -> list[str]:
    """Return text lines for one candidate."""

    reasons = "; ".join(candidate.reasons)
    lines = [
        f"{index}. Hypothesis candidate: {candidate.path}::{candidate.qualname}",
        f"   Why: {reasons}",
        "   Suggested scaffold:",
    ]
    lines.extend(f"     {line}" for line in candidate.suggested_scaffold)
    lines.append(f"   Note: {candidate.note}")
    lines.append("")
    return lines


def render_json(report: HypothesisCandidateReport) -> str:
    """Return stable JSON candidate output."""

    return json.dumps(report.to_json(), indent=2, sort_keys=True)
