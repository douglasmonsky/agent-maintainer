"""Exact repair facts from DocSync reports."""

from __future__ import annotations

from agent_repair_facts.payloads import (
    FactSource,
    fact_payload,
    json_array,
    json_object,
    json_objects,
    read_json,
)


def docsync_report_facts(path: FactSource, check: str) -> list[dict[str, object]]:
    """Return exact facts from a DocSync JSON report."""

    payload = json_object(read_json(path))
    if payload is None:
        return []
    findings = json_objects(payload.get("findings"))
    return [docsync_finding_fact(finding, check) for finding in findings]


def docsync_finding_fact(
    finding: dict[str, object],
    check: str,
) -> dict[str, object]:
    """Return one exact repair fact for a DocSync finding."""

    location = first_location(finding)
    return fact_payload(
        {
            "check": check,
            "path": location.get("path"),
            "line": location.get("line"),
            "column": None,
            "symbol": finding.get("code"),
            "message": finding.get("message"),
            "severity": finding.get("severity"),
        },
    )


def first_location(finding: dict[str, object]) -> dict[str, object]:
    """Return first DocSync finding location normalized for repair facts."""

    locations = json_array(finding.get("locations"))
    if not locations:
        return {}
    location = json_object(locations[0])
    if location is None:
        return {}
    return {
        "path": location.get("path"),
        "line": location.get("start_line"),
    }
