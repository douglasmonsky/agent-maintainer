"""Exact repair facts from DocSync reports."""

from __future__ import annotations

from agent_repair_facts.payloads import FactSource, fact_payload, read_json


def docsync_report_facts(path: FactSource, check: str) -> list[dict[str, object]]:
    """Return exact facts from a DocSync JSON report."""

    payload = read_json(path)
    if not isinstance(payload, dict):
        return []
    findings = payload.get("findings")
    if not isinstance(findings, list):
        return []
    return [
        docsync_finding_fact(finding, check) for finding in findings if isinstance(finding, dict)
    ]


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

    locations = finding.get("locations")
    if not isinstance(locations, list) or not locations:
        return {}
    location = locations[0]
    if not isinstance(location, dict):
        return {}
    return {
        "path": location.get("path"),
        "line": location.get("start_line"),
    }
