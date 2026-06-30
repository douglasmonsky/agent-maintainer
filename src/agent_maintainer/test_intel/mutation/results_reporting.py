"""Render advisory mutation target reports."""

from __future__ import annotations

import json

from agent_maintainer.test_intel.mutation.targets import (
    MutationTarget,
    MutationTargetReport,
)


def render_text(report: MutationTargetReport) -> str:
    """Return human-readable advisory mutation target output."""

    lines = ["Mutation testing targets", ""]
    if report.changed_only:
        lines.extend(render_changed_source(report.changed_source))
    if not report.targets:
        lines.extend(("- <none>", "", f"Note: {report.note}"))
        return "\n".join(lines).rstrip()
    for index, target in enumerate(report.targets, start=1):
        lines.extend(render_target(index, target))
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


def render_target(index: int, target: MutationTarget) -> list[str]:
    """Return text lines for one mutation target."""

    reasons = "; ".join(target.reasons)
    return [
        f"{index}. Mutation target: {target.path}::{target.qualname}",
        f"   Why: {reasons}",
        f"   Suggested focus: {target.suggested_focus}",
        f"   Note: {target.note}",
        "",
    ]


def render_json(report: MutationTargetReport) -> str:
    """Return stable JSON target output."""

    return json.dumps(report.to_json(), indent=2, sort_keys=True)
