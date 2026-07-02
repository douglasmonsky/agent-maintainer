"""Dispatch exact repair fact parsing by check and artifact type."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from agent_maintainer.context.pack import (
    lint_fact_parsers,
    log_fact_parsers,
    pytest_fact_parsers,
    typescript_fact_parsers,
)

FactParser = Callable[[Path, str], list[dict[str, object]]]
FactParserEntry = tuple[str, FactParser]

ARTIFACT_FACT_PARSERS: tuple[FactParserEntry, ...] = (
    ("ruff", lint_fact_parsers.ruff_facts),
    ("pyright", lint_fact_parsers.pyright_facts),
    ("bandit", lint_fact_parsers.bandit_facts),
    ("pytest-coverage", pytest_fact_parsers.pytest_artifact_facts),
)

LOG_FACT_PARSERS: tuple[FactParserEntry, ...] = (
    ("file-length", log_fact_parsers.file_length_facts),
    ("change-budget", log_fact_parsers.change_budget_facts),
    ("typescript-lint", typescript_fact_parsers.typescript_lint_facts),
    ("typescript-typecheck", typescript_fact_parsers.typescript_typecheck_facts),
    ("typescript-test", typescript_fact_parsers.typescript_test_facts),
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
