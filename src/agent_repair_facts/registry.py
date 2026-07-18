"""Dispatch exact repair fact parsing by check and artifact type."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from agent_repair_facts.parsers import (
    docsync,
    java,
    lint,
    logs,
    osv_scanner,
    pytest,
    security,
    typescript,
    typescript_checks,
)
from agent_repair_facts.parsers.typescript_knip import knip_facts
from agent_repair_facts.payloads import FactSource, MemoryFactSource

FactParser = Callable[[FactSource, str], list[dict[str, object]]]
FactParserEntry = tuple[str, FactParser]

ARTIFACT_FACT_PARSERS: tuple[FactParserEntry, ...] = (
    ("ruff", lint.ruff_facts),
    ("pyright", lint.pyright_facts),
    ("bandit", lint.bandit_facts),
    ("pip-audit", security.pip_audit_facts),
    ("osv-scanner", osv_scanner.osv_facts),
    ("pytest-coverage", pytest.pytest_artifact_facts),
    ("typescript-test", typescript.typescript_test_artifact_facts),
    ("docsync", docsync.docsync_report_facts),
    ("java-gradle-static", java.java_artifact_facts),
    ("java-gradle-tests", java.java_artifact_facts),
)

LOG_FACT_PARSERS: tuple[FactParserEntry, ...] = (
    ("architecture-decision", logs.architecture_decision_facts),
    ("file-length", logs.file_length_facts),
    ("change-budget", logs.change_budget_facts),
    ("ruff-format", logs.ruff_format_facts),
    ("pylint", logs.pylint_facts),
    ("typescript-lint", typescript.typescript_lint_facts),
    ("typescript-typecheck", typescript.typescript_typecheck_facts),
    ("typescript-test", typescript.typescript_test_facts),
    ("typescript-knip", knip_facts),
    ("vulture", logs.vulture_facts),
    ("wemake", logs.wemake_facts),
    ("xenon-complexity-gate", logs.xenon_complexity_facts),
)


def artifact_facts(check: str, path: Path) -> list[dict[str, object]]:
    """Return exact facts extracted from one structured artifact."""

    return _source_facts(check, path, ARTIFACT_FACT_PARSERS)


def artifact_facts_from_text(
    check: str,
    path: Path,
    text: str,
) -> list[dict[str, object]]:
    """Return artifact facts without reopening an already-read path."""

    return _source_facts(
        check,
        MemoryFactSource(path, text),
        ARTIFACT_FACT_PARSERS,
    )


def log_facts(check: str, path: Path) -> list[dict[str, object]]:
    """Return exact facts extracted from one check log."""

    return _source_facts(check, path, LOG_FACT_PARSERS)


def log_facts_from_text(
    check: str,
    path: Path,
    text: str,
) -> list[dict[str, object]]:
    """Return log facts without reopening an already-read path."""

    return _source_facts(check, MemoryFactSource(path, text), LOG_FACT_PARSERS)


def find_parser(check: str, parsers: tuple[FactParserEntry, ...]) -> FactParser | None:
    """Return parser matching check name."""
    for name, parser in parsers:
        if check == name:
            return parser
    return None


def _source_facts(
    check: str,
    source: FactSource,
    parsers: tuple[FactParserEntry, ...],
) -> list[dict[str, object]]:
    """Return facts from one path-backed or in-memory source."""

    parser = find_parser(typescript_checks.check_family(check), parsers)
    return parser(source, check) if parser else []
