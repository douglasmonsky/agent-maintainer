"""Dispatch exact repair fact parsing by check and artifact type."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from agent_repair_facts.parsers import (
    docsync,
    java,
    lint,
    osv_scanner,
    pytest,
    security,
    typescript_checks,
    typescript_dependency_cruiser,
    typescript_package_manager_audit,
)
from agent_repair_facts.parsers.logs import (
    architecture_decision_facts,
    change_budget_facts,
    file_length_facts,
    pylint_facts,
    ruff_format_facts,
    vulture_facts,
    wemake_facts,
    xenon_complexity_facts,
)
from agent_repair_facts.parsers.typescript import (
    typescript_lint_facts,
    typescript_test_artifact_facts,
    typescript_test_facts,
    typescript_typecheck_facts,
)
from agent_repair_facts.parsers.typescript_knip import knip_facts
from agent_repair_facts.payloads import FactSource, MemoryFactSource, fact_payload

FactParser = Callable[[FactSource, str], list[dict[str, object]]]
FactParserEntry = tuple[str, FactParser]

ARTIFACT_FACT_PARSERS: tuple[FactParserEntry, ...] = (
    ("ruff", lint.ruff_facts),
    ("pyright", lint.pyright_facts),
    ("bandit", lint.bandit_facts),
    ("pip-audit", security.pip_audit_facts),
    ("osv-scanner", osv_scanner.osv_facts),
    ("pytest-coverage", pytest.pytest_artifact_facts),
    ("typescript-test", typescript_test_artifact_facts),
    ("docsync", docsync.docsync_report_facts),
    ("java-gradle-static", java.java_artifact_facts),
    ("java-gradle-tests", java.java_artifact_facts),
)

LOG_FACT_PARSERS: tuple[FactParserEntry, ...] = (
    ("architecture-decision", architecture_decision_facts),
    ("file-length", file_length_facts),
    ("change-budget", change_budget_facts),
    ("ruff-format", ruff_format_facts),
    ("pylint", pylint_facts),
    ("typescript-lint", typescript_lint_facts),
    ("typescript-typecheck", typescript_typecheck_facts),
    ("typescript-test", typescript_test_facts),
    ("typescript-knip", knip_facts),
    ("typescript-dependency-cruiser", typescript_dependency_cruiser.dependency_cruiser_facts),
    ("vulture", vulture_facts),
    ("wemake", wemake_facts),
    ("xenon-complexity-gate", xenon_complexity_facts),
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
    *,
    structured_parser: str = "",
    structured_parser_manager: str = "",
) -> list[dict[str, object]]:
    """Return log facts without reopening an already-read path."""

    if structured_parser == "typescript-package-manager-audit":
        result = typescript_package_manager_audit.parse_audit_report(
            structured_parser_manager,
            _workspace_label(check),
            path.as_posix(),
            text,
        )
        return [
            fact_payload(
                {
                    "check": check,
                    "path": finding.path,
                    "symbol": finding.advisory_ids[0],
                    "message": typescript_package_manager_audit.format_audit_finding(finding),
                    "severity": finding.severity,
                }
            )
            for finding in result.findings
        ]
    return _source_facts(check, MemoryFactSource(path, text), LOG_FACT_PARSERS)


def _workspace_label(check: str) -> str:
    """Return explicit workspace ownership from a stable check name."""

    return check.partition(":")[2] or "root"


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
