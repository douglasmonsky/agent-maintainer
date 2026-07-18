"""Render advisory TypeScript LCOV changed-line coverage reports."""

from __future__ import annotations

import json

from agent_maintainer.test_intel.typescript_coverage import (
    TypeScriptCoverageFileFact,
    TypeScriptCoverageReport,
)

MAX_TEXT_DETAILS = 50


def render_json(report: TypeScriptCoverageReport) -> str:
    """Return stable JSON report output."""

    return json.dumps(report.to_json(), indent=2, sort_keys=True)


def render_text(report: TypeScriptCoverageReport) -> str:
    """Return bounded human-readable report output."""

    lines = [
        "TypeScript changed-line coverage",
        "",
        f"- artifact: {report.artifact_path}",
        f"- source root: {report.source_root}",
        f"- changed source files: {len(report.changed_source)}",
        f"- matched LCOV files: {report.matched_file_count}",
        f"- missing from LCOV: {len(report.missing_from_lcov)}",
        coverage_summary(report),
        "",
        "Details:",
    ]
    details = [render_file(fact) for fact in report.files]
    details.extend(f"- missing LCOV: {path}" for path in report.missing_from_lcov)
    lines.extend(bounded_details(details))
    lines.extend(("", f"Note: {report.note}"))
    return "\n".join(lines)


def coverage_summary(report: TypeScriptCoverageReport) -> str:
    """Return aggregate changed-line coverage text."""

    percent = report.changed_line_coverage
    if percent is None:
        return "- changed-line coverage: unknown (0 executable changed lines)"
    return (
        f"- changed-line coverage: {percent:.2f}% "
        f"({report.covered_changed_lines}/{report.executable_changed_lines})"
    )


def render_file(fact: TypeScriptCoverageFileFact) -> str:
    """Return one compact per-file detail line."""

    percent = fact.changed_line_coverage
    coverage = "unknown" if percent is None else f"{percent:.2f}%"
    return (
        f"- {fact.path}: {coverage} "
        f"({fact.covered_changed_lines}/{fact.executable_changed_lines}; "
        f"{fact.missed_changed_lines} missed)"
    )


def bounded_details(details: list[str]) -> list[str]:
    """Return at most the configured number of truthful detail lines."""

    if not details:
        return ["- <none>"]
    if len(details) <= MAX_TEXT_DETAILS:
        return details
    retained = details[: MAX_TEXT_DETAILS - 1]
    omitted = len(details) - len(retained)
    return [*retained, f"- ... {omitted} detail line(s) omitted"]
