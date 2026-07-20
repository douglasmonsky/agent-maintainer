"""Normalize explicit npm, pnpm, Yarn, and Bun audit reports."""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath
from typing import cast

from agent_repair_facts.parsers.typescript_package_manager_audit_contract import RawAuditRecord

AUDIT_MANAGERS = frozenset(("npm", "pnpm", "yarn", "bun"))
AUDIT_OUTCOME_CLEAN = "clean"
AUDIT_OUTCOME_FINDINGS = "findings"
AUDIT_OUTCOME_INVALID = "invalid-input"
AUDIT_FACT_LIMIT = 500
AUDIT_LIST_LIMIT = 25
AUDIT_FIELD_CHAR_LIMIT = 200
AUDIT_PATH_CHAR_LIMIT = 500
AUDIT_MESSAGE_CHAR_LIMIT = 1_000
AUDIT_SUMMARY_LINE_LIMIT = 50
TRUNCATION_MARKER_LENGTH = 3

_WHITESPACE_RE = re.compile(r"\s+")
_SEVERITY_RANK = {
    "critical": 0,
    "high": 1,
    "moderate": 2,
    "low": 3,
    "info": 4,
    "unknown": 5,
}
_SEVERITIES = frozenset(_SEVERITY_RANK)
_SCOPES = frozenset(("dev", "prod", "optional", "peer"))
_DIRECTNESS = frozenset(("direct", "indirect"))


@dataclass(frozen=True)
class PackageManagerAuditFinding:
    """One bounded and normalized package-manager audit finding."""

    manager: str
    package: str
    severity: str
    advisory_ids: tuple[str, ...]
    vulnerable_ranges: tuple[str, ...]
    fixed_versions: tuple[str, ...]
    scope: str
    directness: str
    workspace: str
    path: str | None
    source_label: str
    title: str


@dataclass(frozen=True)
class PackageManagerAuditParseResult:
    """Bounded findings and parser outcome for one audit report."""

    manager: str
    workspace: str
    outcome: str
    findings: tuple[PackageManagerAuditFinding, ...]
    supported_count: int
    retained_count: int
    omitted_count: int


AuditAdapter = Callable[[object], tuple[RawAuditRecord, ...] | None]


def parse_audit_report(
    manager: str,
    workspace: str,
    source_label: str,
    text: str,
) -> PackageManagerAuditParseResult:
    """Parse a bounded JSON or NDJSON report using only the explicit manager."""

    normalized_manager = _scalar(manager, limit=AUDIT_FIELD_CHAR_LIMIT).lower()
    normalized_workspace = _scalar(workspace, limit=AUDIT_FIELD_CHAR_LIMIT) or "root"
    normalized_source = _scalar(source_label, limit=AUDIT_FIELD_CHAR_LIMIT) or "<unknown source>"
    if normalized_manager not in AUDIT_MANAGERS:
        return _invalid_result(normalized_manager, normalized_workspace)

    decoded, is_ndjson = _decode_report(text)
    if not decoded:
        return _invalid_result(normalized_manager, normalized_workspace)

    from agent_repair_facts.parsers import typescript_package_manager_audit_adapters as adapters

    supported_container, normalized_records = _parse_decoded_payloads(
        decoded,
        is_ndjson=is_ndjson,
        adapter=adapters.adapter_for(normalized_manager),
        context=(normalized_manager, normalized_workspace, normalized_source),
    )

    if not supported_container:
        return _invalid_result(normalized_manager, normalized_workspace)

    deduped = _deduplicate(normalized_records)
    deduped.sort(key=_finding_sort_key)
    retained = tuple(deduped[:AUDIT_FACT_LIMIT])
    supported_count = len(normalized_records)
    omitted_count = max(0, supported_count - len(retained))
    outcome = AUDIT_OUTCOME_FINDINGS if retained else AUDIT_OUTCOME_CLEAN
    return PackageManagerAuditParseResult(
        manager=normalized_manager,
        workspace=normalized_workspace,
        outcome=outcome,
        findings=retained,
        supported_count=supported_count,
        retained_count=len(retained),
        omitted_count=omitted_count,
    )


def _parse_decoded_payloads(
    decoded: list[object],
    *,
    is_ndjson: bool,
    adapter: AuditAdapter,
    context: tuple[str, str, str],
) -> tuple[bool, list[PackageManagerAuditFinding]]:
    """Apply one pure manager adapter to decoded JSON values."""

    manager, workspace, source_label = context
    supported_container = False
    normalized_records: list[PackageManagerAuditFinding] = []
    for payload in decoded:
        raw_records = adapter(payload)
        if raw_records is None:
            if is_ndjson:
                continue
            return False, []
        supported_container = True
        normalized_records.extend(
            finding
            for raw_record in raw_records
            if (finding := _normalize_record(manager, workspace, source_label, raw_record))
            is not None
        )
    return supported_container, normalized_records


def render_audit_summary(
    result: PackageManagerAuditParseResult,
    *,
    max_lines: int = AUDIT_SUMMARY_LINE_LIMIT,
    max_chars: int = AUDIT_MESSAGE_CHAR_LIMIT,
) -> str:
    """Render deterministic advisory lines within the requested bounds."""

    line_limit = max(1, min(max_lines, AUDIT_SUMMARY_LINE_LIMIT))
    char_limit = max(1, min(max_chars, AUDIT_MESSAGE_CHAR_LIMIT))
    if result.outcome == AUDIT_OUTCOME_INVALID:
        return _truncate(f"{result.manager}: invalid-input; raw audit output retained", char_limit)
    if not result.findings:
        return _truncate(f"{result.manager}: no audit findings", char_limit)

    lines = [format_audit_finding(finding) for finding in result.findings]
    if result.omitted_count:
        lines.append(f"... {result.omitted_count} audit findings omitted")
    if len(lines) > line_limit:
        omitted = len(lines) - line_limit
        lines = lines[: line_limit - 1]
        lines.append(f"... {omitted} audit summary lines omitted")
    return _truncate("\n".join(lines), char_limit)


def format_audit_finding(finding: PackageManagerAuditFinding) -> str:
    """Format one normalized advisory finding with bounded clauses."""

    clauses = [f"{finding.manager}/{finding.workspace}: {finding.package}", finding.severity]
    clauses.extend(
        f"{label}={value}"
        for label, value in (
            ("advisories", ",".join(finding.advisory_ids)),
            ("ranges", ",".join(finding.vulnerable_ranges)),
            ("fixes", ",".join(finding.fixed_versions)),
            ("scope", finding.scope),
            ("directness", finding.directness),
            ("path", finding.path or ""),
            (
                "source",
                finding.source_label if finding.source_label != "<unknown source>" else "",
            ),
        )
        if value
    )
    if finding.title:
        clauses.append(finding.title)
    return _truncate("; ".join(clauses), AUDIT_MESSAGE_CHAR_LIMIT)


def _decode_report(text: str) -> tuple[list[object], bool]:
    """Decode one JSON value or independent non-empty NDJSON lines."""

    try:
        return [json.loads(text)], False
    except (json.JSONDecodeError, RecursionError, TypeError):
        pass
    values: list[object] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            values.append(json.loads(line))
        except (json.JSONDecodeError, RecursionError, TypeError):
            continue
    return values, True


def _normalize_record(
    manager: str,
    workspace: str,
    source_label: str,
    record: RawAuditRecord,
) -> PackageManagerAuditFinding | None:
    """Normalize one adapter record and discard records without repair identity."""

    package = _scalar(record.package)
    advisory_ids = _bounded_values(record.advisory_ids)
    if not package or not advisory_ids:
        return None
    path, path_label = _safe_path(record.path)
    return PackageManagerAuditFinding(
        manager=manager,
        package=package,
        severity=_severity(record.severity),
        advisory_ids=advisory_ids,
        vulnerable_ranges=_bounded_values(record.vulnerable_ranges),
        fixed_versions=_bounded_values(record.fixed_versions),
        scope=_enum(record.scope, _SCOPES),
        directness=_enum(record.directness, _DIRECTNESS),
        workspace=workspace,
        path=path,
        source_label=path_label or source_label,
        title=_scalar(record.title),
    )


def _deduplicate(
    findings: list[PackageManagerAuditFinding],
) -> list[PackageManagerAuditFinding]:
    """Merge exact duplicate facts without combining disagreeing provenance."""

    seen: dict[tuple[object, ...], PackageManagerAuditFinding] = {}
    for finding in findings:
        key = (
            finding.manager,
            finding.workspace,
            finding.package,
            finding.advisory_ids,
            finding.vulnerable_ranges,
            finding.fixed_versions,
            finding.scope,
            finding.directness,
            finding.path,
            finding.source_label,
        )
        previous = seen.get(key)
        if previous is None or finding.title < previous.title:
            seen[key] = finding
    return list(seen.values())


def _finding_sort_key(
    finding: PackageManagerAuditFinding,
) -> tuple[object, ...]:
    """Return deterministic manager/workspace/package/fact ordering."""

    return (
        finding.manager,
        finding.workspace,
        finding.source_label,
        finding.package,
        _SEVERITY_RANK[finding.severity],
        finding.advisory_ids,
        finding.vulnerable_ranges,
        finding.fixed_versions,
    )


def _bounded_values(values: object) -> tuple[str, ...]:
    """Normalize, deduplicate, sort, and retain at most 25 scalar values."""

    if isinstance(values, (str, int)) and not isinstance(values, bool):
        candidates = (values,)
    elif isinstance(values, (list, tuple)):
        candidates = tuple(cast(Iterable[object], values))
    else:
        candidates = ()
    normalized = sorted(
        {_scalar(value) for value in candidates if _scalar(value)},
    )
    return tuple(normalized[:AUDIT_LIST_LIMIT])


def _severity(value: object) -> str:
    """Normalize a documented or unknown upstream severity."""

    normalized = _scalar(value).lower()
    aliases = {"moderate": "moderate", "medium": "moderate"}
    selected = aliases.get(normalized, normalized)
    return selected if selected in _SEVERITIES else "unknown"


def _enum(value: object, allowed: frozenset[str]) -> str:
    """Keep only an explicit bounded enum value."""

    normalized = _scalar(value).lower()
    return normalized if normalized in allowed else ""


def _scalar(value: object, *, limit: int = AUDIT_FIELD_CHAR_LIMIT) -> str:
    """Return bounded single-line text without control characters."""

    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        return ""
    text = str(value)
    text = "".join(" " if unicodedata.category(char) in {"Cc", "Cf"} else char for char in text)
    return _WHITESPACE_RE.sub(" ", text).strip()[:limit]


def _safe_path(value: object) -> tuple[str | None, str]:
    """Return a repository-relative path and safe display label."""

    if not isinstance(value, str) or not value:
        return None, ""
    had_controls = any(unicodedata.category(char) in {"Cc", "Cf"} for char in value)
    normalized_text = value.replace("\\", "/")
    posix_path = PurePosixPath(normalized_text)
    windows_path = PureWindowsPath(value)
    unsafe = (
        had_controls
        or len(value) > AUDIT_PATH_CHAR_LIMIT
        or posix_path.is_absolute()
        or windows_path.is_absolute()
        or bool(windows_path.drive)
        or ".." in posix_path.parts
        or posix_path.as_posix() == "."
    )
    if unsafe:
        basename = _scalar(posix_path.name)
        return None, basename or "<unknown source>"
    normalized = _scalar(posix_path.as_posix(), limit=AUDIT_PATH_CHAR_LIMIT)
    return (normalized or None), (normalized or "<unknown source>")


def _truncate(value: str, limit: int) -> str:
    """Truncate one rendered message while preserving a truthful marker."""

    if len(value) <= limit:
        return value
    if limit <= TRUNCATION_MARKER_LENGTH:
        return value[:limit]
    return f"{value[: limit - TRUNCATION_MARKER_LENGTH].rstrip()}..."


def _invalid_result(manager: str, workspace: str) -> PackageManagerAuditParseResult:
    """Return the fail-closed invalid-input result."""

    return PackageManagerAuditParseResult(
        manager=manager,
        workspace=workspace,
        outcome=AUDIT_OUTCOME_INVALID,
        findings=(),
        supported_count=0,
        retained_count=0,
        omitted_count=0,
    )
