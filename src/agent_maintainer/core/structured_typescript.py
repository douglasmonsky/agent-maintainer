"""Structured summaries for TypeScript provider output."""

from __future__ import annotations

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

TYPESCRIPT_DIAGNOSTIC_LIMIT = 50


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
        or parse_coverage_summary_json(raw_output)
        or parse_lcov_info(raw_output)
    )


def summarize_typescript_check(check_name: str, raw_output: str) -> str | None:
    """Return compact TypeScript provider summary when output is structured."""
    if check_name == "typescript-lint":
        return summarize_typescript_lint(raw_output)
    if check_name == "typescript-typecheck":
        return summarize_typescript_typecheck(raw_output)
    if check_name == "typescript-test":
        return summarize_typescript_test(raw_output)
    return None


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
