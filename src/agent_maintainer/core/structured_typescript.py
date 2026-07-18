"""Structured summaries for TypeScript provider output."""

from __future__ import annotations

from agent_repair_facts.parsers import (
    typescript_checks,
    typescript_dependency_cruiser,
    typescript_knip,
)
from agent_repair_facts.parsers.typescript_coverage import (
    parse_coverage_summary_json,
    parse_lcov_info,
)
from agent_repair_facts.parsers.typescript_diagnostics import (
    TypeScriptDiagnostic,
    format_diagnostic,
    parse_eslint_json,
    parse_jest_json,
    parse_tsc_output,
)
from agent_repair_facts.parsers.typescript_tests import parse_vitest_json

TYPESCRIPT_DIAGNOSTIC_LIMIT = 50
KNIP_SUMMARY_LINE_LIMIT = 50
DEPENDENCY_CRUISER_SUMMARY_LINE_LIMIT = 50


def summarize_typescript_lint(raw_output: str) -> str | None:
    """Return compact summary for ESLint JSON output."""
    return summarize_diagnostics(parse_eslint_json(raw_output))


def summarize_typescript_typecheck(raw_output: str) -> str | None:
    """Return compact summary for TypeScript compiler output."""
    return summarize_diagnostics(parse_tsc_output(raw_output))


def summarize_typescript_test(raw_output: str) -> str | None:
    """Return compact summary for TypeScript test or coverage output."""
    return summarize_diagnostics(
        parse_jest_json(raw_output)
        or parse_vitest_json(raw_output)
        or parse_coverage_summary_json(raw_output)
        or parse_lcov_info(raw_output)
    )


def summarize_typescript_knip(raw_output: str) -> str | None:
    """Return a compact bounded summary for Knip JSON output."""

    parse_result = typescript_knip.parse_knip_json_result(raw_output)
    findings = parse_result.findings
    if not findings:
        return None
    visible_limit = KNIP_SUMMARY_LINE_LIMIT
    if len(findings) > KNIP_SUMMARY_LINE_LIMIT:
        visible_limit -= 1
    visible = findings[:visible_limit]
    lines = [typescript_knip.format_knip_finding(finding) for finding in visible]
    omitted = parse_result.supported_count - len(visible)
    if omitted:
        lines.append(f"... {omitted} more Knip findings omitted. See .verify-logs/")
    return "\n".join(lines)


def summarize_typescript_dependency_cruiser(raw_output: str) -> str | None:
    """Return a compact bounded dependency-cruiser summary."""

    parse_result = (
        typescript_dependency_cruiser.parse_dependency_cruiser_json_result(
            raw_output
        )
    )
    findings = parse_result.findings
    if not findings:
        return None
    visible_limit = DEPENDENCY_CRUISER_SUMMARY_LINE_LIMIT
    if parse_result.supported_count > visible_limit:
        visible_limit -= 1
    visible = findings[:visible_limit]
    lines = [
        typescript_dependency_cruiser.format_dependency_cruiser_finding(finding)
        for finding in visible
    ]
    omitted = parse_result.supported_count - len(visible)
    if omitted:
        lines.append(
            f"... {omitted} more dependency-cruiser findings omitted. "
            "See .verify-logs/"
        )
    return "\n".join(lines)


def summarize_typescript_check(check_name: str, raw_output: str) -> str | None:
    """Return compact TypeScript provider summary when output is structured."""
    summarizers = {
        "typescript-lint": summarize_typescript_lint,
        "typescript-typecheck": summarize_typescript_typecheck,
        "typescript-test": summarize_typescript_test,
        "typescript-knip": summarize_typescript_knip,
        "typescript-dependency-cruiser": summarize_typescript_dependency_cruiser,
    }
    summarizer = summarizers.get(typescript_checks.check_family(check_name))
    if summarizer is None:
        return None
    return summarizer(raw_output)


def summarize_diagnostics(diagnostics: list[TypeScriptDiagnostic]) -> str | None:
    """Return compact bounded TypeScript diagnostics."""
    if not diagnostics:
        return None
    visible = diagnostics[:TYPESCRIPT_DIAGNOSTIC_LIMIT]
    lines = [format_diagnostic(diagnostic) for diagnostic in visible]
    omitted = len(diagnostics) - len(visible)
    if omitted > 0:
        lines.append(
            f"... {omitted} more TypeScript diagnostics omitted. See .verify-logs/",
        )
    return "\n".join(lines)
