"""Tests context contract model fields."""

from __future__ import annotations

from agent_maintainer.context.models import ExactRepairFact


def test_exact_repair_fact_preserves_symbol() -> None:
    """Exact repair facts preserve symbols for deterministic repair loops."""

    fact = ExactRepairFact(
        check="ruff",
        path="src/example.py",
        line=10,
        column=4,
        symbol="F401",
        message="unused import",
        severity="error",
    )

    assert fact.symbol == "F401"
