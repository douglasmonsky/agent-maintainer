"""Exact repair facts for Knip JSON reporter output."""

from __future__ import annotations

import json
from dataclasses import dataclass

from agent_repair_facts.payloads import (
    FactSource,
    fact_payload,
    json_array,
    json_object,
    optional_int,
)

KNIP_FACT_LIMIT = 500
KNIP_CATEGORY_DETAILS = {
    "files": ("knip-unused-file", "Unused file"),
    "exports": ("knip-unused-export", "Unused export"),
    "nsExports": ("knip-unused-export", "Unused export"),
    "types": ("knip-unused-type", "Unused type"),
    "nsTypes": ("knip-unused-type", "Unused type"),
    "dependencies": ("knip-unused-dependency", "Unused dependency"),
    "devDependencies": ("knip-unused-dependency", "Unused dependency"),
    "optionalPeerDependencies": ("knip-unused-dependency", "Unused dependency"),
    "unlisted": ("knip-unlisted-dependency", "Unlisted dependency"),
    "binaries": ("knip-unused-binary", "Unused binary"),
    "unresolved": ("knip-unresolved", "Unresolved import or binary"),
}


@dataclass(frozen=True)
class KnipFinding:
    """One validated and normalized Knip finding."""

    path: str
    category: str
    name: str
    line: int | None
    column: int | None


@dataclass(frozen=True)
class KnipParseResult:
    """Validated Knip findings plus the pre-retention supported count."""

    findings: tuple[KnipFinding, ...]
    supported_count: int
    valid: bool


def parse_knip_json(raw_output: str) -> list[KnipFinding]:
    """Return sorted, bounded findings from Knip JSON output."""

    return list(parse_knip_json_result(raw_output).findings)


def parse_knip_json_result(raw_output: str) -> KnipParseResult:
    """Return bounded findings and parse metadata from Knip JSON output."""

    try:
        payload = json.loads(raw_output)
    except (json.JSONDecodeError, RecursionError):
        return KnipParseResult((), 0, False)
    return _parse_knip_payload_result(payload)


def parse_knip_payload(payload: object) -> list[KnipFinding]:
    """Return supported findings from a decoded Knip payload."""

    return list(_parse_knip_payload_result(payload).findings)


def _parse_knip_payload_result(payload: object) -> KnipParseResult:
    """Return bounded findings and metadata from a decoded Knip payload."""

    root = json_object(payload)
    if root is None:
        return KnipParseResult((), 0, False)
    groups = json_array(root.get("issues"))
    if groups is None:
        return KnipParseResult((), 0, False)
    findings: list[KnipFinding] = []
    for raw_group in groups:
        group = json_object(raw_group)
        if group is None or (path := _text(group.get("file"))) is None:
            continue
        findings.extend(_group_findings(path, group))
    findings.sort(key=_finding_sort_key)
    return KnipParseResult(
        tuple(findings[:KNIP_FACT_LIMIT]),
        len(findings),
        True,
    )


def _group_findings(path: str, group: dict[str, object]) -> list[KnipFinding]:
    """Return supported findings from one Knip file group."""

    findings: list[KnipFinding] = []
    for category in KNIP_CATEGORY_DETAILS:
        items = json_array(group.get(category))
        if items is None:
            continue
        for raw_item in items:
            item = json_object(raw_item)
            if item is None or (name := _finding_name(item)) is None:
                continue
            findings.append(
                KnipFinding(
                    path=path,
                    category=category,
                    name=name,
                    line=optional_int(item.get("line")),
                    column=optional_int(item.get("col"))
                    if item.get("col") is not None
                    else optional_int(item.get("column")),
                )
            )
    return findings


def _finding_name(item: dict[str, object]) -> str | None:
    """Return the first supported Knip finding identity."""

    for key in ("name", "specifier", "namespace", "kind"):
        if name := _text(item.get(key)):
            return name
    return None


def _text(value: object) -> str | None:
    """Return stripped text only for JSON string values."""

    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _finding_sort_key(finding: KnipFinding) -> tuple[str, str, str, int, int]:
    """Return the stable Knip finding order."""

    return (
        finding.path,
        finding.category,
        finding.name,
        finding.line if finding.line is not None else -1,
        finding.column if finding.column is not None else -1,
    )


def finding_symbol(finding: KnipFinding) -> str:
    """Return the stable symbol for one supported Knip category."""

    return KNIP_CATEGORY_DETAILS[finding.category][0]


def finding_message(finding: KnipFinding) -> str:
    """Return the concise message for one Knip finding."""

    label = KNIP_CATEGORY_DETAILS[finding.category][1]
    return f"{label}: {finding.name}"


def format_knip_finding(finding: KnipFinding) -> str:
    """Format one Knip finding without inventing missing locations."""

    location = finding.path
    if finding.line is not None:
        location = f"{location}:{finding.line}"
        if finding.column is not None:
            location = f"{location}:{finding.column}"
    return f"{location}: error: {finding_symbol(finding)}: {finding_message(finding)}"


def knip_facts(path: FactSource, check: str) -> list[dict[str, object]]:
    """Return exact facts from one Knip JSON log."""

    try:
        raw_output = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return [
        fact_payload(
            {
                "check": check,
                "path": finding.path,
                "line": finding.line,
                "column": finding.column,
                "symbol": finding_symbol(finding),
                "message": finding_message(finding),
                "severity": "error",
            }
        )
        for finding in parse_knip_json(raw_output)
    ]
