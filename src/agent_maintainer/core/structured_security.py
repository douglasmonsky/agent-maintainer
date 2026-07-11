"""Structured security scanner artifact summaries."""

from __future__ import annotations

from typing import cast

STRUCTURED_DIAGNOSTIC_LIMIT = 50


def summarize_semgrep_payload(payload: object) -> str | None:
    """Summarize Semgrep JSON findings."""

    report = _json_object(payload)
    if report is None:
        return None
    results = _json_array(report.get("results", []))
    if results is None:
        return None
    findings = [item for value in results if (item := _json_object(value)) is not None]
    lines = [format_semgrep_finding(item) for item in findings[:STRUCTURED_DIAGNOSTIC_LIMIT]]
    append_omitted(lines, len(findings), "Semgrep findings", "semgrep.json")
    return "\n".join(lines) if lines else None


def format_semgrep_finding(finding: dict[str, object]) -> str:
    """Format one Semgrep finding without full source context."""

    start = _json_object(finding.get("start", {})) or {}
    extra = _json_object(finding.get("extra", {})) or {}
    line = int_value(start.get("line"), default=1)
    col = int_value(start.get("col"), default=1)
    message = str_value(extra.get("message"))
    severity = str_value(extra.get("severity"))
    rule_id = str_value(finding.get("check_id"), default="semgrep")
    path = str_value(finding.get("path"), default="<unknown>")
    return f"{path}:{line}:{col}: {rule_id} {severity}: {message}".strip()


def summarize_osv_payload(payload: object) -> str | None:
    """Summarize OSV Scanner JSON vulnerabilities."""

    report = _json_object(payload)
    if report is None:
        return None
    lines: list[str] = []
    for value in _json_array(report.get("results", [])) or []:
        if (result := _json_object(value)) is not None:
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
    packages = _json_array(result.get("packages", []))
    if packages is None:
        return lines
    for value in packages:
        package = _json_object(value)
        if package is None:
            continue
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

    values = _json_array(payload)
    if values is None:
        return None
    findings = [item for value in values if (item := _json_object(value)) is not None]
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

    report = _json_object(payload)
    if report is None:
        return None
    dependencies = _json_array(report.get("dependencies", []))
    if dependencies is None:
        return None
    lines: list[str] = []
    for value in dependencies:
        if (dependency := _json_object(value)) is not None:
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
    vulns = _json_array(dependency.get("vulns", []))
    if vulns is None:
        return []
    lines: list[str] = []
    for value in vulns:
        if (vuln := _json_object(value)) is not None:
            lines.append(format_pip_audit_vulnerability(name, version, vuln))
    return lines


def format_pip_audit_vulnerability(
    name: str,
    version: str,
    vuln: dict[str, object],
) -> str:
    """Format one pip-audit vulnerability."""

    vuln_id = str_value(vuln.get("id"), default="PYSEC")
    fix_versions = _json_array(vuln.get("fix_versions", []))
    fix_text = ""
    if fix_versions:
        versions = ", ".join(map(str, fix_versions))
        fix_text = f" fix: {versions}"
    prefix = f"{name} {version}: {vuln_id}"
    return f"{prefix}{fix_text}"


def osv_package_name(package: dict[str, object]) -> str:
    """Return OSV package name with ecosystem when available."""

    raw_package = _json_object(package.get("package", {}))
    if raw_package is None:
        return "<unknown>"
    name = str_value(raw_package.get("name"), default="<unknown>")
    ecosystem = str_value(raw_package.get("ecosystem"), default="")
    return f"{ecosystem}/{name}" if ecosystem else name


def vulnerabilities(package: dict[str, object]) -> list[dict[str, object]]:
    """Return vulnerability dictionaries from OSV package payload."""

    raw_vulns = _json_array(package.get("vulnerabilities", []))
    if raw_vulns is None:
        return []
    return [vuln for value in raw_vulns if (vuln := _json_object(value)) is not None]


def osv_vulnerability_count(payload: dict[str, object]) -> int:
    """Return total OSV vulnerability count."""

    count = 0
    results = _json_array(payload.get("results", []))
    if results is None:
        return count
    for value in results:
        result = _json_object(value)
        if result is None:
            continue
        packages = _json_array(result.get("packages", []))
        if packages is None:
            continue
        for package_value in packages:
            if (package := _json_object(package_value)) is not None:
                count += len(vulnerabilities(package))
    return count


def pip_audit_vulnerability_count(dependencies: list[object]) -> int:
    """Return total pip-audit vulnerability count."""

    count = 0
    for value in dependencies:
        dependency = _json_object(value)
        if dependency is None:
            continue
        vulns = _json_array(dependency.get("vulns", []))
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


def _json_object(value: object) -> dict[str, object] | None:
    """Return a JSON object with string keys, or ``None`` when malformed."""

    if not isinstance(value, dict):
        return None
    raw = cast(dict[object, object], value)
    if not all(isinstance(key, str) for key in raw):
        return None
    return {key: item for key, item in raw.items() if isinstance(key, str)}


def _json_array(value: object) -> list[object] | None:
    """Return a JSON array with an explicit element boundary."""

    if not isinstance(value, list):
        return None
    return cast(list[object], value)
