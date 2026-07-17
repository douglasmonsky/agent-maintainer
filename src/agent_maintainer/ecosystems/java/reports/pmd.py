"""Bounded PMD XML report adapter."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from agent_maintainer.ecosystems.java.findings import JavaFinding
from agent_maintainer.ecosystems.java.reports.xml import (
    JavaXmlError,
    XmlElement,
    XmlLimits,
    bounded_report_text,
    local_name,
    normalized_report_path,
    parse_bounded_xml,
)

COMPLEXITY_VALUE = re.compile(r"\bcomplexity(?:\s+of|\s*:)?\s+(\d+)\b", re.IGNORECASE)


@dataclass(frozen=True)
class PmdReport:
    """One validated PMD report."""

    findings: tuple[JavaFinding, ...]


def parse_pmd_report(
    path: Path,
    *,
    gradle_root: Path,
    limits: XmlLimits | None = None,
) -> PmdReport:
    """Parse PMD findings from bounded complete XML evidence."""
    selected_limits = limits or XmlLimits()
    root = parse_bounded_xml(path, limits=selected_limits)
    if local_name(root.tag) != "pmd":
        raise JavaXmlError("unsupported PMD report root")
    if any(local_name(element.tag) == "error" for element in root.iter()):
        raise JavaXmlError("incomplete PMD analysis report")
    findings = _parse_files(root, gradle_root=gradle_root)
    if len(findings) > selected_limits.max_findings:
        raise JavaXmlError("PMD report exceeds finding limit")
    return PmdReport(tuple(findings))


def _parse_files(root: XmlElement, *, gradle_root: Path) -> list[JavaFinding]:
    findings: list[JavaFinding] = []
    files = (element for element in root.iter() if local_name(element.tag) == "file")
    for file_element in files:
        violations = tuple(child for child in file_element if local_name(child.tag) == "violation")
        if not violations:
            continue
        reported_path = file_element.attrib.get("name", "")
        if not reported_path.strip():
            raise JavaXmlError("PMD file name is missing")
        source_path = normalized_report_path(reported_path, gradle_root=gradle_root)
        findings.extend(_parse_violation(item, source_path) for item in violations)
    return findings


def _parse_violation(element: XmlElement, source_path: str) -> JavaFinding:
    rule = element.attrib.get("rule", "").strip()
    if not rule:
        raise JavaXmlError("PMD violation is missing rule")
    raw_message = " ".join("".join(element.itertext()).split()) or rule
    message = bounded_report_text(raw_message, fallback=rule)
    try:
        return JavaFinding(
            tool="pmd",
            rule=rule,
            path=source_path,
            subject=_subject(element, rule),
            message=message,
            severity=_severity(element.attrib.get("priority")),
            line=_optional_line(element.attrib.get("beginline")),
            metric=_complexity_metric(rule, raw_message),
        )
    except ValueError as exc:
        raise JavaXmlError("malformed PMD finding") from exc


def _subject(element: XmlElement, rule: str) -> str:
    class_name = element.attrib.get("class", "").strip()
    method_name = element.attrib.get("method", "").strip()
    if class_name and method_name:
        return f"{class_name}#{method_name}"
    return class_name or method_name or rule


def _severity(value: str | None) -> str:
    if value is None or not value.strip():
        return "warning"
    try:
        priority = int(value)
    except ValueError as exc:
        raise JavaXmlError("malformed PMD priority") from exc
    severities = ("error", "error", "warning", "info", "info")
    if priority < 1 or priority > len(severities):
        raise JavaXmlError("malformed PMD priority")
    return severities[priority - 1]


def _optional_line(value: str | None) -> int | None:
    if value is None or not value.strip():
        return None
    try:
        line = int(value)
    except ValueError as exc:
        raise JavaXmlError("malformed PMD line") from exc
    if line < 1:
        raise JavaXmlError("malformed PMD line")
    return line


def _complexity_metric(rule: str, message: str) -> int | None:
    if "complexity" not in rule.lower() and "complexity" not in message.lower():
        return None
    match = COMPLEXITY_VALUE.search(message)
    return None if match is None else int(match.group(1))
