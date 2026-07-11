"""Parse lint and type-checker exact repair facts."""

from __future__ import annotations

from agent_repair_facts import payloads


def ruff_facts(path: payloads.FactSource, check: str) -> list[dict[str, object]]:
    """Return exact facts from Ruff JSON output."""

    return [ruff_fact(check, item) for item in payloads.json_objects(payloads.read_json(path))]


def ruff_fact(check: str, item: dict[str, object]) -> dict[str, object]:
    """Return one Ruff exact fact."""

    location = item.get("location", {})
    return payloads.fact_payload(
        {
            "check": check,
            "path": item.get("filename"),
            "line": payloads.location_value(location, "row"),
            "column": payloads.location_value(location, "column"),
            "symbol": item.get("code"),
            "message": item.get("message"),
            "severity": "error",
        },
    )


def pyright_facts(path: payloads.FactSource, check: str) -> list[dict[str, object]]:
    """Return exact facts from Pyright JSON output."""

    payload = payloads.json_object(payloads.read_json(path))
    if payload is None:
        return []
    diagnostics = payloads.json_objects(payload.get("generalDiagnostics"))
    return [pyright_fact(check, item) for item in diagnostics]


def pyright_fact(check: str, item: dict[str, object]) -> dict[str, object]:
    """Return one Pyright exact fact."""

    start = range_start(item.get("range"))
    return payloads.fact_payload(
        {
            "check": check,
            "path": item.get("file"),
            "line": payloads.one_based(start.get("line")),
            "column": payloads.one_based(start.get("character")),
            "symbol": item.get("rule"),
            "message": item.get("message"),
            "severity": item.get("severity"),
        },
    )


def bandit_facts(path: payloads.FactSource, check: str) -> list[dict[str, object]]:
    """Return exact facts from Bandit JSON output."""

    payload = payloads.json_object(payloads.read_json(path))
    if payload is None:
        return []
    results = payloads.json_objects(payload.get("results"))
    return [bandit_fact(check, item) for item in results]


def bandit_fact(check: str, item: dict[str, object]) -> dict[str, object]:
    """Return one Bandit exact fact."""

    return payloads.fact_payload(
        {
            "check": check,
            "path": item.get("filename"),
            "line": payloads.optional_int(item.get("line_number")),
            "column": payloads.optional_int(item.get("col_offset")),
            "symbol": item.get("test_id"),
            "message": item.get("issue_text"),
            "severity": payloads.lower_text(item.get("issue_severity")) or "error",
        },
    )


def range_start(value: object) -> dict[str, object]:
    """Return Pyright diagnostic range start mapping."""

    parsed = payloads.json_object(value)
    if parsed is None:
        return {}
    return payloads.json_object(parsed.get("start")) or {}
