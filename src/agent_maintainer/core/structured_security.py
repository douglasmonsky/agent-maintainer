"""Structured security scanner artifact summaries."""

from __future__ import annotations

from agent_maintainer.core.structured_values import json_array, json_object, json_objects
from agent_repair_facts.parsers import osv_scanner

STRUCTURED_DIAGNOSTIC_LIMIT = 50


def summarize_semgrep_payload(payload: object) -> str | None:
    """Summarize Semgrep JSON findings."""

    report = json_object(payload)
    if report is None:
        return None
    results = json_array(report.get("results", []))
    if results is None:
        return None
    findings = json_objects(results)
    lines = [format_semgrep_finding(item) for item in findings[:STRUCTURED_DIAGNOSTIC_LIMIT]]
    append_omitted(lines, len(findings), "Semgrep findings", "semgrep.json")
    return "\n".join(lines) if lines else None


def format_semgrep_finding(finding: dict[str, object]) -> str:
    """Format one Semgrep finding without full source context."""

    start = json_object(finding.get("start", {})) or {}
    extra = json_object(finding.get("extra", {})) or {}
    line = int_value(start.get("line"), default=1)
    col = int_value(start.get("col"), default=1)
    message = str_value(extra.get("message"))
    severity = str_value(extra.get("severity"))
    rule_id = str_value(finding.get("check_id"), default="semgrep")
    path = str_value(finding.get("path"), default="<unknown>")
    return f"{path}:{line}:{col}: {rule_id} {severity}: {message}".strip()


def summarize_osv_payload(payload: object) -> str | None:
    """Summarize OSV Scanner JSON vulnerabilities."""

    parsed = osv_scanner.parse_osv_payload(payload)
    if not parsed.valid or not parsed.findings:
        return None
    visible_limit = STRUCTURED_DIAGNOSTIC_LIMIT
    if parsed.supported_count > STRUCTURED_DIAGNOSTIC_LIMIT:
        visible_limit -= 1
    lines = [osv_scanner.format_osv_finding(finding) for finding in parsed.findings[:visible_limit]]
    omitted = parsed.supported_count - visible_limit
    if omitted > 0:
        lines.append(
            f"... {omitted} more OSV vulnerabilities omitted. See .verify-logs/osv-scanner.json",
        )
    return "\n".join(lines)


def summarize_gitleaks_payload(payload: object) -> str | None:
    """Summarize Gitleaks findings without printing secret values."""

    values = json_array(payload)
    if values is None:
        return None
    findings = json_objects(values)
    lines = [format_gitleaks_finding(item) for item in findings[:STRUCTURED_DIAGNOSTIC_LIMIT]]
    append_omitted(lines, len(findings), "secret-scan findings", "secret-scan.json")
    return "\n".join(lines) if lines else None


def format_gitleaks_finding(finding: dict[str, object]) -> str:
    """Format one Gitleaks finding while intentionally omitting secret text."""

    path = str_value(finding.get("File"), default="<unknown>")
    line = int_value(finding.get("StartLine"), default=1)
    column = int_value(finding.get("StartColumn"), default=1)
    rule_id = str_value(finding.get("RuleID"), default="gitleaks")
    description = str_value(finding.get("Description"), default="")
    return f"{path}:{line}:{column}: {rule_id}: {description}".rstrip()


def summarize_pip_audit_payload(payload: object) -> str | None:
    """Summarize pip-audit JSON vulnerabilities."""

    report = json_object(payload)
    if report is None:
        return None
    dependencies = json_array(report.get("dependencies", []))
    if dependencies is None:
        return None
    lines: list[str] = []
    for dependency in json_objects(dependencies):
        lines.extend(pip_audit_dependency_lines(dependency))
        if len(lines) >= STRUCTURED_DIAGNOSTIC_LIMIT:
            break
    append_omitted(
        lines,
        pip_audit_vulnerability_count(dependencies),
        "pip-audit findings",
        "pip-audit.json",
    )
    return "\n".join(lines) if lines else None


def pip_audit_dependency_lines(dependency: dict[str, object]) -> list[str]:
    """Return formatted pip-audit vulnerability lines for one dependency."""

    name = str_value(dependency.get("name"), default="<unknown>")
    version = str_value(dependency.get("version"), default="?")
    vulns = json_array(dependency.get("vulns", []))
    if vulns is None:
        return []
    lines: list[str] = []
    for vuln in json_objects(vulns):
        lines.append(format_pip_audit_vulnerability(name, version, vuln))
    return lines


def format_pip_audit_vulnerability(
    name: str,
    version: str,
    vuln: dict[str, object],
) -> str:
    """Format one pip-audit vulnerability."""

    vuln_id = str_value(vuln.get("id"), default="PYSEC")
    fix_versions = json_array(vuln.get("fix_versions", []))
    fix_text = ""
    if fix_versions:
        versions = ", ".join(map(str, fix_versions))
        fix_text = f" fix: {versions}"
    prefix = f"{name} {version}: {vuln_id}"
    return f"{prefix}{fix_text}"


def pip_audit_vulnerability_count(dependencies: list[object]) -> int:
    """Return total pip-audit vulnerability count."""

    count = 0
    for dependency in json_objects(dependencies):
        vulns = json_array(dependency.get("vulns", []))
        if vulns is not None:
            count += len(vulns)
    return count


def append_omitted(
    lines: list[str],
    total: int,
    label: str,
    artifact_name: str,
) -> None:
    """Append omitted-count line for truncated structured findings."""

    omitted = total - min(total, STRUCTURED_DIAGNOSTIC_LIMIT)
    if omitted > 0:
        lines.append(f"... {omitted} more {label} omitted. See .verify-logs/{artifact_name}")


def int_value(value: object, *, default: int = 0) -> int:
    """Return integer value with safe fallback."""

    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return default
    try:
        return int(value)
    except ValueError:
        return default


def str_value(value: object, *, default: str = "") -> str:
    """Return string value with default for missing data."""

    if value is None:
        return default
    return str(value)
