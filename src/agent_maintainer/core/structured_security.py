"""Structured security scanner artifact summaries."""

from __future__ import annotations

from agent_maintainer.core.structured_values import json_array, json_object, json_objects

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

    report = json_object(payload)
    if report is None:
        return None
    lines: list[str] = []
    results = json_array(report.get("results", [])) or []
    for result in json_objects(results):
        lines.extend(osv_result_lines(result))
        if len(lines) >= STRUCTURED_DIAGNOSTIC_LIMIT:
            break
    append_omitted(
        lines,
        osv_vulnerability_count(report),
        "OSV vulnerabilities",
        "osv-scanner.json",
    )
    return "\n".join(lines) if lines else None


def osv_result_lines(result: dict[str, object]) -> list[str]:
    """Return formatted OSV vulnerability lines for one result object."""

    lines: list[str] = []
    packages = json_array(result.get("packages", []))
    if packages is None:
        return lines
    for package in json_objects(packages):
        lines.extend(osv_package_lines(package))
        if len(lines) >= STRUCTURED_DIAGNOSTIC_LIMIT:
            return lines
    return lines


def osv_package_lines(package: dict[str, object]) -> list[str]:
    """Return formatted OSV vulnerability lines for one package."""

    package_name = osv_package_name(package)
    version = str_value(package.get("version"), default="?")
    lines: list[str] = []
    for vuln in vulnerabilities(package):
        vuln_id = str_value(vuln.get("id"), default="OSV")
        summary = str_value(vuln.get("summary"), default="")
        lines.append(f"{package_name} {version}: {vuln_id}: {summary}".rstrip())
    return lines


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


def osv_package_name(package: dict[str, object]) -> str:
    """Return OSV package name with ecosystem when available."""

    raw_package = json_object(package.get("package", {}))
    if raw_package is None:
        return "<unknown>"
    name = str_value(raw_package.get("name"), default="<unknown>")
    ecosystem = str_value(raw_package.get("ecosystem"), default="")
    return f"{ecosystem}/{name}" if ecosystem else name


def vulnerabilities(package: dict[str, object]) -> list[dict[str, object]]:
    """Return vulnerability dictionaries from OSV package payload."""

    raw_vulns = json_array(package.get("vulnerabilities", []))
    if raw_vulns is None:
        return []
    return json_objects(raw_vulns)


def osv_vulnerability_count(payload: dict[str, object]) -> int:
    """Return total OSV vulnerability count."""

    count = 0
    results = json_array(payload.get("results", []))
    if results is None:
        return count
    for result in json_objects(results):
        packages = json_array(result.get("packages", []))
        if packages is None:
            continue
        count += sum(len(vulnerabilities(package)) for package in json_objects(packages))
    return count


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
