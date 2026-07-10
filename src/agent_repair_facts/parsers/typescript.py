"""Exact repair facts for TypeScript provider logs."""

from __future__ import annotations

from collections.abc import Callable

from agent_repair_facts.parsers.typescript_coverage import (
    parse_coverage_summary_json,
    parse_lcov_info,
)
from agent_repair_facts.parsers.typescript_diagnostics import (
    TypeScriptDiagnostic,
    parse_eslint_json,
    parse_jest_json,
    parse_tsc_output,
)
from agent_repair_facts.parsers.typescript_tests import parse_vitest_json
from agent_repair_facts.payloads import FactSource, fact_payload


def typescript_lint_facts(path: FactSource, check: str) -> list[dict[str, object]]:
    """Return exact facts from ESLint JSON log output."""
    return diagnostic_facts(read_diagnostics(path, parse_eslint_json), check)


def typescript_typecheck_facts(path: FactSource, check: str) -> list[dict[str, object]]:
    """Return exact facts from TypeScript compiler log output."""
    return diagnostic_facts(read_diagnostics(path, parse_tsc_output), check)


def typescript_test_facts(path: FactSource, check: str) -> list[dict[str, object]]:
    """Return exact facts from TypeScript test JSON log output."""
    return diagnostic_facts(read_diagnostics(path, parse_typescript_test_json), check)


def parse_typescript_test_json(raw_output: str) -> list[TypeScriptDiagnostic]:
    """Parse supported TypeScript test JSON outputs."""
    return parse_jest_json(raw_output) or parse_vitest_json(raw_output)


def typescript_test_artifact_facts(
    path: FactSource,
    check: str,
) -> list[dict[str, object]]:
    """Return exact facts from TypeScript test artifacts."""
    if path.name == "coverage-summary.json":
        return diagnostic_facts(read_diagnostics(path, parse_coverage_summary_json), check)
    if path.name == "lcov.info" or path.suffix == ".lcov":
        return diagnostic_facts(read_diagnostics(path, parse_lcov_info), check)
    return []


def read_diagnostics(
    path: FactSource,
    parser: Callable[[str], list[TypeScriptDiagnostic]],
) -> list[TypeScriptDiagnostic]:
    """Read and parse a TypeScript diagnostic log."""
    try:
        raw_output = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return parser(raw_output)


def diagnostic_facts(
    diagnostics: list[TypeScriptDiagnostic],
    check: str,
) -> list[dict[str, object]]:
    """Return exact facts for parsed TypeScript diagnostics."""
    return [
        fact_payload(
            {
                "check": check,
                "path": diagnostic.path,
                "line": diagnostic.line,
                "column": diagnostic.column,
                "symbol": diagnostic.code,
                "message": diagnostic.message,
                "severity": diagnostic.severity,
            },
        )
        for diagnostic in diagnostics
    ]
