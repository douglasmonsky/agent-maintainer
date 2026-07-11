"""Render repair-fact coverage assessment."""

from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from typing import cast

from agent_maintainer.assess.repair_fact_coverage_models import (
    RepairFactCheckCoverage,
    RepairFactCoverageReport,
    RepairFactParserTarget,
)


def render_text(report: RepairFactCoverageReport) -> str:
    """Render compact repair-fact coverage text."""

    coverage_line = (
        f"Coverage: {report.coverage_percent:.1f}% "
        f"({report.structured_checks}/{report.failed_checks} failed checks)"
    )
    lines = [
        "Repair-Fact Coverage",
        f"Target: {report.target}",
        f"Manifest: {display_value(report.manifest_path)}",
        f"Run ID: {display_value(report.run_id)}",
        f"Profile: {display_value(report.profile)}",
        f"Status: {report.status}",
        coverage_line,
        "",
        "Failed checks:",
        *_check_lines(report.checks),
        "",
        "Next parser targets:",
        *_target_lines(report.parser_targets),
        "",
        "Next commands:",
        *[f"- `{command}`" for command in report.next_commands],
    ]
    return "\n".join(lines)


def render_json(report: RepairFactCoverageReport) -> str:
    """Render stable JSON repair-fact coverage payload."""

    return json.dumps(to_dict(report), indent=2, sort_keys=True)


def _check_lines(checks: tuple[RepairFactCheckCoverage, ...]) -> list[str]:
    """Return compact lines for failed checks."""

    if checks:
        return [
            (
                f"- {check.check}: structured={check.structured_facts}, "
                f"fallback={check.fallback_facts}, log_bytes={check.log_bytes}"
            )
            for check in checks
        ]
    return ["- None"]


def _target_lines(targets: tuple[RepairFactParserTarget, ...]) -> list[str]:
    """Return compact lines for ranked parser targets."""

    if targets:
        return [
            (
                f"- {target.check}: fallback_failures={target.fallback_failures}, "
                f"log_bytes={target.total_log_bytes}. {target.recommendation}"
            )
            for target in targets
        ]
    return ["- None"]


def to_dict(value: object) -> object:
    """Return JSON-serializable dataclass payload."""

    if isinstance(value, tuple):
        values = cast(tuple[object, ...], value)
        return [to_dict(item) for item in values]
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: to_dict(getattr(value, field.name)) for field in fields(value)}
    return value


def display_value(value: str | None) -> str:
    """Return printable optional value."""

    return value or "<none>"
