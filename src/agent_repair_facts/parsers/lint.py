"""Parse lint and type-checker exact repair facts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_repair_facts.payloads import (
    fact_payload,
    location_value,
    lower_text,
    one_based,
    optional_int,
    read_json,
)


def ruff_facts(path: Path, check: str) -> list[dict[str, object]]:
    """Return exact facts from Ruff JSON output."""

    payload = read_json(path)
    if not isinstance(payload, list):
        return []
    return [ruff_fact(check, item) for item in payload if isinstance(item, dict)]


def ruff_fact(check: str, item: dict[str, Any]) -> dict[str, object]:
    """Return one Ruff exact fact."""

    location = item.get("location", {})
    return fact_payload(
        {
            "check": check,
            "path": item.get("filename"),
            "line": location_value(location, "row"),
            "column": location_value(location, "column"),
            "symbol": item.get("code"),
            "message": item.get("message"),
            "severity": "error",
        },
    )


def pyright_facts(path: Path, check: str) -> list[dict[str, object]]:
    """Return exact facts from Pyright JSON output."""

    payload = read_json(path)
    if not isinstance(payload, dict):
        return []
    diagnostics = payload.get("generalDiagnostics", [])
    if not isinstance(diagnostics, list):
        return []
    return [pyright_fact(check, item) for item in diagnostics if isinstance(item, dict)]


def pyright_fact(check: str, item: dict[str, Any]) -> dict[str, object]:
    """Return one Pyright exact fact."""

    start = range_start(item.get("range"))
    return fact_payload(
        {
            "check": check,
            "path": item.get("file"),
            "line": one_based(start.get("line")),
            "column": one_based(start.get("character")),
            "symbol": item.get("rule"),
            "message": item.get("message"),
            "severity": item.get("severity"),
        },
    )


def bandit_facts(path: Path, check: str) -> list[dict[str, object]]:
    """Return exact facts from Bandit JSON output."""

    payload = read_json(path)
    if not isinstance(payload, dict):
        return []
    results = payload.get("results", [])
    if not isinstance(results, list):
        return []
    return [bandit_fact(check, item) for item in results if isinstance(item, dict)]


def bandit_fact(check: str, item: dict[str, Any]) -> dict[str, object]:
    """Return one Bandit exact fact."""

    return fact_payload(
        {
            "check": check,
            "path": item.get("filename"),
            "line": optional_int(item.get("line_number")),
            "column": optional_int(item.get("col_offset")),
            "symbol": item.get("test_id"),
            "message": item.get("issue_text"),
            "severity": lower_text(item.get("issue_severity")) or "error",
        },
    )


def range_start(value: object) -> dict[str, object]:
    """Return Pyright diagnostic range start mapping."""

    if not isinstance(value, dict):
        return {}
    start = value.get("start", {})
    return start if isinstance(start, dict) else {}
