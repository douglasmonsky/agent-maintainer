"""Bounded Checkstyle XML report adapter."""

from __future__ import annotations

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

CHECK_SUFFIX = "Check"


@dataclass(frozen=True)
class CheckstyleReport:
    """One validated Checkstyle report."""

    findings: tuple[JavaFinding, ...]


def parse_checkstyle_report(
    path: Path,
    *,
    gradle_root: Path,
    limits: XmlLimits | None = None,
) -> CheckstyleReport:
    """Parse Checkstyle findings from bounded complete XML evidence."""
    selected_limits = limits or XmlLimits()
    root = parse_bounded_xml(path, limits=selected_limits)
    if local_name(root.tag) != "checkstyle":
        raise JavaXmlError("unsupported Checkstyle report root")
    if any(local_name(element.tag) == "exception" for element in root.iter()):
        raise JavaXmlError("incomplete Checkstyle analysis report")
    findings = _parse_files(root, gradle_root=gradle_root)
    if len(findings) > selected_limits.max_findings:
        raise JavaXmlError("Checkstyle report exceeds finding limit")
    return CheckstyleReport(tuple(findings))


def _parse_files(root: XmlElement, *, gradle_root: Path) -> list[JavaFinding]:
    findings: list[JavaFinding] = []
    files = (element for element in root.iter() if local_name(element.tag) == "file")
    for file_element in files:
        errors = tuple(child for child in file_element if local_name(child.tag) == "error")
        if not errors:
            continue
        reported_path = file_element.attrib.get("name", "")
        if not reported_path.strip():
            raise JavaXmlError("Checkstyle file name is missing")
        source_path = normalized_report_path(reported_path, gradle_root=gradle_root)
        findings.extend(_parse_error(error, source_path) for error in errors)
    return findings


def _parse_error(element: XmlElement, source_path: str) -> JavaFinding:
    rule = _rule_name(element.attrib.get("source", ""))
    message = bounded_report_text(element.attrib.get("message", ""), fallback=rule)
    severity = element.attrib.get("severity", "warning") or "warning"
    try:
        return JavaFinding(
            tool="checkstyle",
            rule=rule,
            path=source_path,
            subject=rule,
            message=message,
            severity=severity,
            line=_optional_line(element.attrib.get("line")),
        )
    except ValueError as exc:
        raise JavaXmlError("malformed Checkstyle finding") from exc


def _rule_name(source: str) -> str:
    rule = source.strip().rsplit(".", maxsplit=1)[-1]
    if rule.endswith(CHECK_SUFFIX):
        rule = rule[: -len(CHECK_SUFFIX)]
    return rule or "checkstyle"


def _optional_line(value: str | None) -> int | None:
    if value is None or not value.strip():
        return None
    try:
        line = int(value)
    except ValueError as exc:
        raise JavaXmlError("malformed Checkstyle line") from exc
    if line < 1:
        raise JavaXmlError("malformed Checkstyle line")
    return line
