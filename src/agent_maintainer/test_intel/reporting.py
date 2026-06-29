"""Render test intelligence reports."""

from __future__ import annotations

import json

from agent_maintainer.test_intel.models import TestIntelReport, TestMatch


def suggested_actions(matches: tuple[TestMatch, ...]) -> tuple[str, ...]:
    """Return deterministic next actions from ranked matches."""

    if not matches:
        return ("Add or update focused tests for changed source.",)
    seen: set[str] = set()
    actions: list[str] = []
    for match in matches:
        if match.pytest_command not in seen:
            seen.add(match.pytest_command)
            actions.append(f"Run: {match.pytest_command}")
    return tuple(actions)


def render_text(report: TestIntelReport) -> str:
    """Return human-readable report."""

    lines = ["Test intelligence changed source", ""]
    lines.extend(render_changed_source(report.changed_source))
    lines.extend(render_likely_tests(report.likely_tests))
    lines.extend(render_coverage(report))
    lines.extend(render_suggested_actions(report.suggested_actions))
    return "\n".join(lines).rstrip()


def render_changed_source(changed_source: tuple[str, ...]) -> list[str]:
    """Return changed-source report lines."""

    lines = ["Changed source:"]
    if changed_source:
        lines.extend(f"- {path}" for path in changed_source)
    else:
        lines.append("- <none>")
    lines.append("")
    return lines


def render_likely_tests(matches: tuple[TestMatch, ...]) -> list[str]:
    """Return likely-test report lines."""

    lines = ["Likely test files:"]
    if not matches:
        lines.extend(("- <none>", ""))
        return lines
    for index, match in enumerate(matches, start=1):
        lines.extend(render_match(index, match))
    lines.append("")
    return lines


def render_match(index: int, match: TestMatch) -> list[str]:
    """Return report lines for one ranked test match."""

    lines = [
        f"{index}. {match.test_path}",
        f"   source: {match.source_path}",
        f"   confidence: {match.confidence}",
        "   reasons:",
    ]
    lines.extend(f"   - {reason}" for reason in match.reasons)
    return lines


def render_coverage(report: TestIntelReport) -> list[str]:
    """Return coverage report lines."""

    coverage = report.coverage
    source_percent = coverage.changed_source_file_coverage
    line_percent = coverage.changed_line_coverage
    gaps = coverage.branch_coverage_gaps
    lines = ["Coverage:"]
    if source_percent is None:
        lines.append("- changed source-file coverage: unknown")
    else:
        lines.append(f"- changed source-file coverage: {source_percent:.2f}%")
    if line_percent is None:
        lines.append("- changed-line coverage: unknown")
    else:
        lines.append(f"- changed-line coverage: {line_percent:.2f}%")
    if gaps is None:
        lines.append("- branch coverage gaps: unknown")
    else:
        lines.append(f"- branch coverage gaps: {gaps}")
    lines.append("")
    return lines


def render_suggested_actions(actions: tuple[str, ...]) -> list[str]:
    """Return suggested action report lines."""

    lines = ["Suggested next actions:"]
    lines.extend(f"{index}. {action}" for index, action in enumerate(actions, start=1))
    return lines


def render_json(report: TestIntelReport) -> str:
    """Return stable JSON report."""

    return json.dumps(report.to_json(), indent=2, sort_keys=True)
