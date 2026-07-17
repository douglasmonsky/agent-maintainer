"""Exact repair facts for Knip JSON reporter output."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath
from types import MappingProxyType
from typing import Final

from agent_repair_facts.payloads import (
    FactSource,
    fact_payload,
    json_array,
    json_object,
    optional_int,
)

KNIP_FACT_LIMIT = 500
KnipCategoryDetails = tuple[str, str]
KNIP_CATEGORY_DETAILS: Final[Mapping[str, KnipCategoryDetails]] = MappingProxyType(
    {
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
)


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


def _parse_knip_payload_result(payload: object) -> KnipParseResult:
    """Return bounded findings and metadata from a decoded Knip payload."""

    root = json_object(payload)
    if root is None:
        return KnipParseResult((), 0, False)
    groups = json_array(root.get("issues"))
    if groups is None:
        return KnipParseResult((), 0, False)
    findings = _top_level_file_findings(root)
    for raw_group in groups:
        group = json_object(raw_group)
        if group is None:
            continue
        path = _repository_path(group.get("file"))
        if path is None:
            continue
        findings.extend(_group_findings(path, group))
    findings.sort(key=_finding_sort_key)
    return KnipParseResult(
        tuple(findings[:KNIP_FACT_LIMIT]),
        len(findings),
        True,
    )


def _top_level_file_findings(root: dict[str, object]) -> list[KnipFinding]:
    """Return unused-file findings from Knip's top-level `files` array."""

    files = json_array(root.get("files"))
    if files is None:
        return []
    findings: list[KnipFinding] = []
    for raw_path in files:
        path = _repository_path(raw_path)
        if path is None:
            continue
        findings.append(KnipFinding(path, "files", path, None, None))
    return findings


def _group_findings(path: str, group: dict[str, object]) -> list[KnipFinding]:
    """Return supported findings from one Knip file group."""

    findings: list[KnipFinding] = []
    for category in KNIP_CATEGORY_DETAILS:
        if category == "files":
            continue
        items = json_array(group.get(category))
        if items is None:
            continue
        findings.extend(_category_findings(path, category, items))
    return findings


def _category_findings(
    path: str,
    category: str,
    items: list[object],
) -> list[KnipFinding]:
    """Return validated findings for one Knip issue category."""

    findings: list[KnipFinding] = []
    for raw_item in items:
        item = json_object(raw_item)
        if item is None:
            continue
        name = _finding_name(item)
        if name is None:
            continue
        findings.append(
            KnipFinding(
                path=path,
                category=category,
                name=name,
                line=optional_int(item.get("line")),
                column=_column(item),
            )
        )
    return findings


def _finding_name(item: dict[str, object]) -> str | None:
    """Return the first supported Knip finding identity."""

    for key in ("name", "specifier", "namespace", "kind"):
        name = _text(item.get(key))
        if name:
            return name
    return None


def _text(value: object) -> str | None:
    """Return stripped text only for JSON string values."""

    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _repository_path(value: object) -> str | None:
    """Return a normalized repository-relative path or reject unsafe paths."""

    text = _text(value)
    if text is None:
        return None
    windows_path = PureWindowsPath(text)
    normalized = PurePosixPath(text.replace("\\", "/"))
    if normalized.is_absolute() or windows_path.is_absolute() or windows_path.drive:
        return None
    if ".." in normalized.parts or normalized.as_posix() == ".":
        return None
    return normalized.as_posix()


def _column(item: dict[str, object]) -> int | None:
    """Return Knip's current `col` value or the compatible `column` fallback."""

    column = optional_int(item.get("col"))
    if column is None:
        return optional_int(item.get("column"))
    return column


def _sort_position(value: int | None) -> int:
    """Return a stable sort value for an optional source position."""

    if value is None:
        return -1
    return value


def _finding_sort_key(finding: KnipFinding) -> tuple[str, str, str, int, int]:
    """Return the stable Knip finding order."""

    return (
        finding.path,
        finding.category,
        finding.name,
        _sort_position(finding.line),
        _sort_position(finding.column),
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
