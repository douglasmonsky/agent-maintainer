"""Render advisory mutation sweep reports."""

from __future__ import annotations

import json

from agent_maintainer.test_intel.mutation_sweep import (
    MutationSweepCandidate,
    MutationSweepReport,
)


def render_text(report: MutationSweepReport) -> str:
    """Return human-readable mutation sweep output."""

    lines = ["Mutation sweep candidates", ""]
    if report.changed_only:
        lines.extend(render_changed_source(report.changed_source))
    lines.extend(render_stop_conditions(report.stop_conditions))
    if not report.candidates:
        lines.extend(("- <none>", "", f"Note: {report.note}"))
        return "\n".join(lines).rstrip()
    for index, candidate in enumerate(report.candidates, start=1):
        lines.extend(render_candidate(index, candidate))
    lines.extend(("Suggested workflow:", f"- {report.note}"))
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


def render_stop_conditions(stop_conditions: tuple[str, ...]) -> list[str]:
    """Return configured stop condition lines."""

    lines = ["Stop conditions:"]
    lines.extend(f"- {condition}" for condition in stop_conditions)
    lines.append("")
    return lines


def render_candidate(index: int, candidate: MutationSweepCandidate) -> list[str]:
    """Return text lines for one mutation sweep candidate."""

    reasons = "; ".join(candidate.reasons)
    tests = ", ".join(candidate.likely_tests) if candidate.likely_tests else "<none>"
    targets = ", ".join(candidate.target_qualnames) if candidate.target_qualnames else "<none>"
    return [
        f"{index}. Sweep candidate: {candidate.path}",
        f" Score: {candidate.score}",
        f" Why: {reasons}",
        f" Suggested only_mutate: {candidate.suggested_only_mutate}",
        f" Suggested targets: {targets}",
        f" Suggested tests: {tests}",
        f" Command after config update: {candidate.suggested_command}",
        "",
    ]


def render_json(report: MutationSweepReport) -> str:
    """Return stable JSON sweep output."""

    return json.dumps(report.to_json(), indent=2, sort_keys=True)
