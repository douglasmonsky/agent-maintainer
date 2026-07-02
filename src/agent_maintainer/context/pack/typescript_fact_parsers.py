"""Exact repair facts for TypeScript provider logs."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from agent_maintainer.context.pack.fact_payloads import fact_payload
from agent_maintainer.ecosystems.typescript.diagnostics import (
    TypeScriptDiagnostic,
    parse_eslint_json,
    parse_jest_json,
    parse_tsc_output,
)


def typescript_lint_facts(path: Path, check: str) -> list[dict[str, object]]:
    """Return exact facts from ESLint JSON log output."""
    return diagnostic_facts(read_diagnostics(path, parse_eslint_json), check)


def typescript_typecheck_facts(path: Path, check: str) -> list[dict[str, object]]:
    """Return exact facts from TypeScript compiler log output."""
    return diagnostic_facts(read_diagnostics(path, parse_tsc_output), check)


def typescript_test_facts(path: Path, check: str) -> list[dict[str, object]]:
    """Return exact facts from Jest-compatible JSON test output."""
    return diagnostic_facts(read_diagnostics(path, parse_jest_json), check)


def read_diagnostics(
    path: Path,
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
