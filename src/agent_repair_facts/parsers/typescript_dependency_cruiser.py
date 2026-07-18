"""Exact repair facts for dependency-cruiser cruise-result JSON output."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath

from agent_repair_facts.payloads import FactSource, fact_payload, json_array, json_object

DEPENDENCY_CRUISER_FACT_LIMIT = 500
DEPENDENCY_CRUISER_FIELD_CHAR_LIMIT = 200
DEPENDENCY_CRUISER_PATH_CHAR_LIMIT = 500
DEPENDENCY_CRUISER_MESSAGE_CHAR_LIMIT = 1_000

SUPPORTED_SEVERITIES = frozenset(("error", "warn", "info"))
SUPPORTED_TYPES = frozenset(
    ("dependency", "module", "reachability", "cycle", "instability", "folder")
)

_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class DependencyCruiserFinding:
    """One validated and normalized dependency-cruiser violation."""

    source_path: str | None
    source_label: str
    target_label: str
    rule: str
    severity: str
    violation_type: str | None


@dataclass(frozen=True)
class DependencyCruiserParseResult:
    """Bounded findings plus the pre-retention supported count."""

    findings: tuple[DependencyCruiserFinding, ...]
    supported_count: int
    valid: bool


def parse_dependency_cruiser_json_result(
    raw_output: str,
) -> DependencyCruiserParseResult:
    """Return bounded findings and metadata from cruise-result JSON text."""

    try:
        payload = json.loads(raw_output)
    except (json.JSONDecodeError, RecursionError):
        return DependencyCruiserParseResult((), 0, False)
    root = json_object(payload)
    if root is None:
        return DependencyCruiserParseResult((), 0, False)
    summary = json_object(root.get("summary"))
    if summary is None:
        return DependencyCruiserParseResult((), 0, False)
    violations = json_array(summary.get("violations"))
    if violations is None:
        return DependencyCruiserParseResult((), 0, False)

    findings = [
        finding
        for raw_violation in violations
        if (finding := _parse_violation(raw_violation)) is not None
    ]
    findings.sort(key=_finding_sort_key)
    return DependencyCruiserParseResult(
        tuple(findings[:DEPENDENCY_CRUISER_FACT_LIMIT]),
        len(findings),
        True,
    )


def _parse_violation(raw_violation: object) -> DependencyCruiserFinding | None:
    """Return one supported violation without affecting neighboring entries."""

    violation = json_object(raw_violation)
    if violation is None:
        return None
    source = _source_details(violation.get("from"))
    if source is None:
        return None
    source_path, source_label = source

    target_label = _target_label(violation)
    if target_label is None:
        return None
    rule = _rule_details(violation.get("rule"))
    if rule is None:
        return None
    rule_name, severity = rule
    type_supported, violation_type = _violation_type(violation.get("type"))
    if not type_supported:
        return None
    return DependencyCruiserFinding(
        source_path=source_path,
        source_label=source_label,
        target_label=target_label,
        rule=rule_name,
        severity=severity,
        violation_type=violation_type,
    )


def _source_details(value: object) -> tuple[str | None, str] | None:
    """Return targetability and display data for a usable source identity."""

    if _text(value) is None:
        return None
    source = _safe_path(value, "<unknown source>")
    return None if source[1] == "<unknown source>" else source


def _rule_details(value: object) -> tuple[str, str] | None:
    """Return a supported dependency-cruiser rule name and severity."""

    rule = json_object(value)
    if rule is None:
        return None
    name = _text(rule.get("name"))
    severity = _text(rule.get("severity"))
    if name is None or severity not in SUPPORTED_SEVERITIES:
        return None
    return name, severity


def _violation_type(value: object) -> tuple[bool, str | None]:
    """Distinguish an omitted optional type from an unsupported type."""

    if value is None:
        return True, None
    violation_type = _text(value)
    return violation_type in SUPPORTED_TYPES, violation_type


def _target_label(violation: dict[str, object]) -> str | None:
    """Return the usable target or the unresolved-target fallback."""

    target = _text(violation.get("to"))
    if target is not None:
        _target_path, label = _safe_path(violation.get("to"), "<unknown target>")
        if label != "<unknown target>":
            return label
    unresolved = _text(violation.get("unresolvedTo"))
    if unresolved is None:
        return None
    _unresolved_path, label = _safe_path(
        violation.get("unresolvedTo"),
        "<unknown target>",
    )
    return label if label != "<unknown target>" else None


def _text(value: object) -> str | None:
    """Return bounded single-line text only for JSON strings."""

    if not isinstance(value, str):
        return None
    text = _single_line(value)
    if not text:
        return None
    return text[:DEPENDENCY_CRUISER_FIELD_CHAR_LIMIT]


def _single_line(value: str) -> str:
    """Collapse controls and whitespace without applying a length bound."""

    without_controls = _CONTROL_RE.sub(" ", value)
    return _WHITESPACE_RE.sub(" ", without_controls).strip()


def _safe_path(value: object, unknown_label: str) -> tuple[str | None, str]:
    """Return a repository target plus a bounded, non-sensitive display label."""

    if not isinstance(value, str):
        return None, unknown_label
    had_controls = _CONTROL_RE.search(value) is not None
    text = _single_line(value)
    if not text:
        return None, unknown_label
    windows_path = PureWindowsPath(text)
    posix_path = PurePosixPath(text.replace("\\", "/"))
    unsafe = (
        had_controls
        or len(text) > DEPENDENCY_CRUISER_PATH_CHAR_LIMIT
        or posix_path.is_absolute()
        or windows_path.is_absolute()
        or bool(windows_path.drive)
        or ".." in posix_path.parts
        or posix_path.as_posix() == "."
    )
    if unsafe:
        return None, _safe_basename(posix_path, unknown_label)
    normalized = posix_path.as_posix()
    return normalized, normalized[:DEPENDENCY_CRUISER_FIELD_CHAR_LIMIT]


def _safe_basename(path: PurePosixPath, unknown_label: str) -> str:
    """Return an independently safe basename for a rejected path."""

    name = _single_line(path.name)
    if not name or name in {".", ".."}:
        return unknown_label
    return name[:DEPENDENCY_CRUISER_FIELD_CHAR_LIMIT]


def _finding_sort_key(
    finding: DependencyCruiserFinding,
) -> tuple[str, str, str, str, str]:
    """Return the stable dependency-cruiser finding order."""

    return (
        finding.source_label,
        finding.target_label,
        finding.rule,
        finding.severity,
        finding.violation_type or "",
    )


def format_dependency_cruiser_finding(
    finding: DependencyCruiserFinding,
) -> str:
    """Format one bounded single-line architecture finding."""

    details = finding.severity
    if finding.violation_type:
        details = f"{details}; {finding.violation_type}"
    message = (
        f"{finding.source_label} -> {finding.target_label}: "
        f"{finding.rule} [{details}]"
    )
    if len(message) <= DEPENDENCY_CRUISER_MESSAGE_CHAR_LIMIT:
        return message
    return f"{message[: DEPENDENCY_CRUISER_MESSAGE_CHAR_LIMIT - 3].rstrip()}..."


def dependency_cruiser_facts(
    path: FactSource,
    check: str,
) -> list[dict[str, object]]:
    """Return exact facts from one dependency-cruiser JSON log."""

    try:
        raw_output = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    result = parse_dependency_cruiser_json_result(raw_output)
    return [
        fact_payload(
            {
                "check": check,
                "path": finding.source_path,
                "symbol": finding.rule,
                "message": format_dependency_cruiser_finding(finding),
                "severity": finding.severity,
            }
        )
        for finding in result.findings
    ]
