"""Structured summaries for TypeScript provider output."""

from __future__ import annotations

from agent_maintainer.ecosystems.typescript.diagnostics import (
    TypeScriptDiagnostic,
    format_diagnostic,
    parse_eslint_json,
    parse_tsc_output,
)

TYPESCRIPT_DIAGNOSTIC_LIMIT = 50


def summarize_typescript_lint(raw_output: str) -> str | None:
    """Return compact summary for ESLint JSON output."""
    return summarize_diagnostics(parse_eslint_json(raw_output))


def summarize_typescript_typecheck(raw_output: str) -> str | None:
    """Return compact summary for TypeScript compiler output."""
    return summarize_diagnostics(parse_tsc_output(raw_output))


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
