"""Extract exact repair facts from verifier artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_maintainer.context.failures import FailureRecord

MAX_FACTS_PER_CHECK = 5


def repair_facts(log_dir: Path, records: tuple[FailureRecord, ...]) -> list[dict[str, object]]:
    """Return bounded exact repair facts for failed checks."""
    facts: list[dict[str, object]] = []
    for record in records:
        extracted = structured_facts(log_dir, record)
        facts.extend(extracted[:MAX_FACTS_PER_CHECK] or [generic_fact(record)])
    return facts


def structured_facts(log_dir: Path, record: FailureRecord) -> list[dict[str, object]]:
    """Return facts extracted from known structured artifacts."""
    facts: list[dict[str, object]] = []
    for artifact_path in record.artifact_paths:
        path = resolved_artifact_path(log_dir, artifact_path)
        if record.name == "ruff":
            facts.extend(ruff_facts(path, record.name))
        elif record.name == "pyright":
            facts.extend(pyright_facts(path, record.name))
        elif record.name == "bandit":
            facts.extend(bandit_facts(path, record.name))
    return facts


def resolved_artifact_path(log_dir: Path, artifact_path: str) -> Path:
    """Return artifact path from manifest path text."""
    path = Path(artifact_path)
    if path.is_absolute() or path.exists():
        return path
    return log_dir / path.name


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


def generic_fact(record: FailureRecord) -> dict[str, object]:
    """Return generic fact when no structured artifact facts exist."""
    return fact_payload(
        {
            "check": record.name,
            "path": None,
            "line": None,
            "column": None,
            "symbol": None,
            "message": failure_message(record),
            "severity": "error",
        },
    )


def fact_payload(values: dict[str, object]) -> dict[str, object]:
    """Return normalized exact repair fact payload."""
    return {
        "check": str(values.get("check") or "unknown"),
        "path": optional_text(values.get("path")),
        "line": optional_int(values.get("line")),
        "column": optional_int(values.get("column")),
        "symbol": optional_text(values.get("symbol")),
        "message": str(values.get("message") or "").strip(),
        "severity": lower_text(values.get("severity")) or "error",
    }


def read_json(path: Path) -> object | None:
    """Return JSON artifact payload when available."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def range_start(value: object) -> dict[str, object]:
    """Return Pyright diagnostic range start mapping."""
    if not isinstance(value, dict):
        return {}
    start = value.get("start", {})
    return start if isinstance(start, dict) else {}


def location_value(location: object, key: str) -> int | None:
    """Return integer location value from a mapping."""
    if not isinstance(location, dict):
        return None
    return optional_int(location.get(key))


def one_based(value: object) -> int | None:
    """Return one-based integer for zero-based artifact value."""
    integer = optional_int(value)
    return None if integer is None else integer + 1


def optional_int(value: object) -> int | None:
    """Return integer values only."""
    return value if isinstance(value, int) else None


def optional_text(value: object) -> str | None:
    """Return non-empty string values."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def lower_text(value: object) -> str | None:
    """Return lower-cased optional text."""
    text = optional_text(value)
    return text.lower() if text else None


def failure_message(record: FailureRecord) -> str:
    """Return exact message for one failed check record."""
    exit_text = "unknown" if record.exit_code is None else str(record.exit_code)
    return f"{record.name} failed with exit code {exit_text}"
