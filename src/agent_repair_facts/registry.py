"""Dispatch exact repair fact parsing by check and artifact type."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from agent_repair_facts.parsers import docsync, lint, logs, pytest, typescript

FactParser = Callable[[Path, str], list[dict[str, object]]]
FactParserEntry = tuple[str, FactParser]

ARTIFACT_FACT_PARSERS: tuple[FactParserEntry, ...] = (
    ("ruff", lint.ruff_facts),
    ("pyright", lint.pyright_facts),
    ("bandit", lint.bandit_facts),
    ("pytest-coverage", pytest.pytest_artifact_facts),
    ("docsync", docsync.docsync_report_facts),
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
    ("vulture", logs.vulture_facts),
    ("wemake", logs.wemake_facts),
    ("xenon-complexity-gate", logs.xenon_complexity_facts),
)


def artifact_facts(check: str, path: Path) -> list[dict[str, object]]:
    """Return exact facts extracted from one structured artifact."""

    parser = find_parser(check, ARTIFACT_FACT_PARSERS)
    return parser(path, check) if parser else []


def log_facts(check: str, path: Path) -> list[dict[str, object]]:
    """Return exact facts extracted from one check log."""

    parser = find_parser(check, LOG_FACT_PARSERS)
    return parser(path, check) if parser else []


def find_parser(check: str, parsers: tuple[FactParserEntry, ...]) -> FactParser | None:
    """Return parser matching check name."""
    for name, parser in parsers:
        if check == name:
            return parser
    return None
