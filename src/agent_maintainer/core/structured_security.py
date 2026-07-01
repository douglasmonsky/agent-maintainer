"""Structured security scanner artifact summaries."""

from __future__ import annotations

STRUCTURED_DIAGNOSTIC_LIMIT = 50


def summarize_semgrep_payload(payload: object) -> str | None:
    """Summarize Semgrep JSON findings."""

    if not isinstance(payload, dict):
        return None
    results = payload.get("results", [])
    if not isinstance(results, list):
        return None
    findings = [item for item in results if isinstance(item, dict)]
    lines = [format_semgrep_finding(item) for item in findings[:STRUCTURED_DIAGNOSTIC_LIMIT]]
    append_omitted(lines, len(findings), "Semgrep findings", "semgrep.json")
    return "\n".join(lines) if lines else None


def format_semgrep_finding(finding: dict[str, object]) -> str:
    """Format one Semgrep finding without full source context."""

    start = finding.get("start", {})
    extra = finding.get("extra", {})
    line = int_value(start.get("line") if isinstance(start, dict) else None, default=1)
    col = int_value(start.get("col") if isinstance(start, dict) else None, default=1)
    message = str_value(extra.get("message") if isinstance(extra, dict) else "")
    severity = str_value(extra.get("severity") if isinstance(extra, dict) else "")
    rule_id = str_value(finding.get("check_id"), default="semgrep")
    path = str_value(finding.get("path"), default="<unknown>")
    return f"{path}:{line}:{col}: {rule_id} {severity}: {message}".strip()


def summarize_osv_payload(payload: object) -> str | None:
    """Summarize OSV Scanner JSON vulnerabilities."""

    if not isinstance(payload, dict):
        return None
    lines: list[str] = []
    for result in payload.get("results", []):
        if isinstance(result, dict):
            lines.extend(osv_result_lines(result))
        if len(lines) >= STRUCTURED_DIAGNOSTIC_LIMIT:
            break
    append_omitted(
        lines,
        osv_vulnerability_count(payload),
        "OSV vulnerabilities",
        "osv-scanner.json",
    )
    return "\n".join(lines) if lines else None


def osv_result_lines(result: dict[str, object]) -> list[str]:
    """Return formatted OSV vulnerability lines for one result object."""

    lines: list[str] = []
    packages = result.get("packages", [])
    if not isinstance(packages, list):
        return lines
    for package in packages:
        if not isinstance(package, dict):
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

    if not isinstance(payload, list):
        return None
    findings = [item for item in payload if isinstance(item, dict)]
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

    if not isinstance(payload, dict):
        return None
    dependencies = payload.get("dependencies", [])
    if not isinstance(dependencies, list):
        return None
    lines: list[str] = []
    for dependency in dependencies:
        if isinstance(dependency, dict):
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
    vulns = dependency.get("vulns", [])
    if not isinstance(vulns, list):
        return []
    lines: list[str] = []
    for vuln in vulns:
        if isinstance(vuln, dict):
            lines.append(format_pip_audit_vulnerability(name, version, vuln))
    return lines


def format_pip_audit_vulnerability(
    name: str,
    version: str,
    vuln: dict[str, object],
) -> str:
    """Format one pip-audit vulnerability."""

    vuln_id = str_value(vuln.get("id"), default="PYSEC")
    fix_versions = vuln.get("fix_versions", [])
    fix_text = ""
    if isinstance(fix_versions, list) and fix_versions:
        versions = ", ".join(map(str, fix_versions))
        fix_text = f" fix: {versions}"
    prefix = f"{name} {version}: {vuln_id}"
    return f"{prefix}{fix_text}"


def osv_package_name(package: dict[str, object]) -> str:
    """Return OSV package name with ecosystem when available."""

    raw_package = package.get("package", {})
    if not isinstance(raw_package, dict):
        return "<unknown>"
    name = str_value(raw_package.get("name"), default="<unknown>")
    ecosystem = str_value(raw_package.get("ecosystem"), default="")
    return f"{ecosystem}/{name}" if ecosystem else name


def vulnerabilities(package: dict[str, object]) -> list[dict[str, object]]:
    """Return vulnerability dictionaries from OSV package payload."""

    raw_vulns = package.get("vulnerabilities", [])
    if not isinstance(raw_vulns, list):
        return []
    return [vuln for vuln in raw_vulns if isinstance(vuln, dict)]


def osv_vulnerability_count(payload: dict[str, object]) -> int:
    """Return total OSV vulnerability count."""

    count = 0
    results = payload.get("results", [])
    if not isinstance(results, list):
        return count
    for result in results:
        if not isinstance(result, dict):
            continue
        packages = result.get("packages", [])
        if not isinstance(packages, list):
            continue
        for package in packages:
            if isinstance(package, dict):
                count += len(vulnerabilities(package))
    return count


def pip_audit_vulnerability_count(dependencies: list[object]) -> int:
    """Return total pip-audit vulnerability count."""

    count = 0
    for dependency in dependencies:
        if not isinstance(dependency, dict):
            continue
        vulns = dependency.get("vulns", [])
        if isinstance(vulns, list):
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
