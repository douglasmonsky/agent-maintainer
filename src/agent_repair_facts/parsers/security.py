"""Parse structured dependency-security repair facts."""

from __future__ import annotations

from agent_repair_facts import payloads


def pip_audit_facts(
    path: payloads.FactSource,
    check: str,
) -> list[dict[str, object]]:
    """Return one exact repair fact for every pip-audit vulnerability."""

    report = payloads.json_object(payloads.read_json(path))
    if report is None:
        return []
    facts: list[dict[str, object]] = []
    for dependency in payloads.json_objects(report.get("dependencies")):
        facts.extend(dependency_facts(dependency, check))
    return facts


def dependency_facts(
    dependency: dict[str, object],
    check: str,
) -> list[dict[str, object]]:
    """Return pip-audit facts for one dependency entry."""

    name = payloads.optional_text(dependency.get("name")) or "<unknown>"
    version = payloads.optional_text(dependency.get("version")) or "<unknown>"
    return [
        vulnerability_fact(check, name, version, vulnerability)
        for vulnerability in payloads.json_objects(dependency.get("vulns"))
    ]


def vulnerability_fact(
    check: str,
    package: str,
    version: str,
    vulnerability: dict[str, object],
) -> dict[str, object]:
    """Normalize one pip-audit vulnerability."""

    advisory = payloads.optional_text(vulnerability.get("id")) or "<unknown>"
    message = f"{package} {version}: {advisory}"
    aliases = text_values(vulnerability.get("aliases"))
    if aliases:
        joined_aliases = ", ".join(aliases)
        message = f"{message} ({joined_aliases})"
    details: list[str] = []
    fixes = text_values(vulnerability.get("fix_versions"))
    if fixes:
        joined_fixes = ", ".join(fixes)
        details.append(f"fix: {joined_fixes}")
    description = payloads.optional_text(vulnerability.get("description"))
    if description:
        details.append(description)
    if details:
        message = "; ".join((message, *details))
    return payloads.fact_payload(
        {
            "check": check,
            "symbol": advisory,
            "message": message,
            "severity": "error",
        },
    )


def text_values(value: object) -> list[str]:
    """Return non-empty strings from a decoded JSON array."""

    values = payloads.json_array(value) or []
    return [text for item in values if (text := payloads.optional_text(item))]
