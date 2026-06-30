"""Dispatch exact repair fact parsing by check and artifact type."""

from __future__ import annotations

from pathlib import Path

from agent_maintainer.context.pack import (
    lint_fact_parsers,
    log_fact_parsers,
    pytest_fact_parsers,
)


def artifact_facts(check: str, path: Path) -> list[dict[str, object]]:
    """Return exact facts extracted from one structured artifact."""

    if check == "ruff":
        return lint_fact_parsers.ruff_facts(path, check)
    if check == "pyright":
        return lint_fact_parsers.pyright_facts(path, check)
    if check == "bandit":
        return lint_fact_parsers.bandit_facts(path, check)
    if check == "pytest-coverage":
        return pytest_fact_parsers.pytest_artifact_facts(path, check)
    return []


def log_facts(check: str, path: Path) -> list[dict[str, object]]:
    """Return exact facts extracted from one check log."""

    if check == "file-length":
        return log_fact_parsers.file_length_facts(path, check)
    if check == "change-budget":
        return log_fact_parsers.change_budget_facts(path, check)
    return []
