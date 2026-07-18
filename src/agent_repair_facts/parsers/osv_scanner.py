"""Parse bounded OSV Scanner v2 findings and exact repair facts."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import chain
from pathlib import PurePosixPath, PureWindowsPath
from typing import Final

from agent_repair_facts import payloads

OSV_FACT_LIMIT: Final = 500
OSV_SUMMARY_CHAR_LIMIT: Final = 200


@dataclass(frozen=True)
class OsvFinding:
    """One normalized alias-grouped OSV vulnerability."""

    path: str | None
    source_label: str
    source_type: str
    ecosystem: str
    package: str
    version: str
    advisory: str
    aliases: tuple[str, ...]
    fixed_versions: tuple[str, ...]
    max_severity: str | None
    summary: str | None


@dataclass(frozen=True)
class OsvParseResult:
    """Bounded normalized OSV findings plus pre-retention metadata."""

    findings: tuple[OsvFinding, ...]
    supported_count: int
    valid: bool


@dataclass(frozen=True)
class _SourceInfo:
    path: str | None
    label: str
    source_type: str


@dataclass(frozen=True)
class _PackageInfo:
    source: _SourceInfo
    ecosystem: str
    name: str
    version: str
    vulnerabilities: dict[str, dict[str, object]]


def parse_osv_payload(payload: object) -> OsvParseResult:
    """Return safe, sorted, alias-grouped findings from OSV Scanner JSON."""

    root = payloads.json_object(payload)
    if root is None:
        return OsvParseResult((), 0, False)
    results = payloads.json_array(root.get("results"))
    if results is None:
        return OsvParseResult((), 0, False)
    findings: list[OsvFinding] = []
    for result in payloads.json_objects(results):
        findings.extend(_result_findings(result))
    findings.sort(key=_finding_sort_key)
    return OsvParseResult(
        tuple(findings[:OSV_FACT_LIMIT]),
        len(findings),
        True,
    )


def osv_facts(
    source: payloads.FactSource,
    check: str,
) -> list[dict[str, object]]:
    """Return exact repair facts from one OSV Scanner artifact."""

    parsed = parse_osv_payload(payloads.read_json(source))
    return [_fact(check, finding) for finding in parsed.findings]


def format_osv_finding(finding: OsvFinding) -> str:
    """Return one concise, path-safe OSV finding line."""

    package_name = "/".join((finding.ecosystem, finding.package))
    base = f"{package_name} {finding.version}: {finding.advisory}"
    if finding.aliases:
        aliases = ", ".join(finding.aliases)
        base = f"{base} ({aliases})"
    details = [f"source: {finding.source_label}"]
    if finding.fixed_versions:
        fixed_versions = ", ".join(finding.fixed_versions)
        details.append(f"fix: {fixed_versions}")
    if finding.max_severity:
        details.append(f"severity: {finding.max_severity}")
    if finding.summary:
        details.append(finding.summary)
    return "; ".join((base, *details))


def _result_findings(result: dict[str, object]) -> list[OsvFinding]:
    raw_source = payloads.json_object(result.get("source")) or {}
    path, label = _safe_source_path(raw_source.get("path"))
    source_type = _text(raw_source.get("type")) or "unknown"
    source = _SourceInfo(path, label, source_type)
    findings: list[OsvFinding] = []
    for item in payloads.json_objects(result.get("packages")):
        findings.extend(_package_findings(source, item))
    return findings


def _package_findings(
    source: _SourceInfo,
    item: dict[str, object],
) -> list[OsvFinding]:
    package_info = payloads.json_object(item.get("package"))
    if package_info is None:
        return []
    name = _text(package_info.get("name"))
    version = _text(package_info.get("version")) or _text(item.get("version"))
    if name is None or version is None:
        return []
    ecosystem = _text(package_info.get("ecosystem")) or "<unknown>"
    vulnerabilities = {
        advisory: vulnerability
        for vulnerability in payloads.json_objects(item.get("vulnerabilities"))
        for advisory in (_text(vulnerability.get("id")),)
        if advisory is not None
    }
    package = _PackageInfo(
        source=source,
        ecosystem=ecosystem,
        name=name,
        version=version,
        vulnerabilities=vulnerabilities,
    )
    return _grouped_and_fallback_findings(
        package,
        item.get("groups"),
    )


def _grouped_and_fallback_findings(
    package: _PackageInfo,
    raw_groups: object,
) -> list[OsvFinding]:
    referenced: set[str] = set()
    findings: list[OsvFinding] = []
    for group in payloads.json_objects(raw_groups):
        ids = tuple(
            sorted(
                set(_text_values(group.get("ids"))) & package.vulnerabilities.keys(),
            ),
        )
        if not ids:
            continue
        referenced.update(ids)
        findings.append(
            _group_finding(
                package,
                ids,
                group,
            ),
        )
    for advisory in sorted(package.vulnerabilities.keys() - referenced):
        findings.append(
            _fallback_finding(
                package,
                advisory,
                package.vulnerabilities[advisory],
            ),
        )
    return findings


def _group_finding(
    package: _PackageInfo,
    ids: tuple[str, ...],
    group: dict[str, object],
) -> OsvFinding:
    canonical = ids[0]
    records = tuple(package.vulnerabilities[advisory] for advisory in ids)
    aliases = set(ids[1:])
    aliases.update(_text_values(group.get("aliases")))
    for record in records:
        aliases.update(_text_values(record.get("aliases")))
    aliases.discard(canonical)
    return OsvFinding(
        path=package.source.path,
        source_label=package.source.label,
        source_type=package.source.source_type,
        ecosystem=package.ecosystem,
        package=package.name,
        version=package.version,
        advisory=canonical,
        aliases=tuple(sorted(aliases)),
        fixed_versions=_fixed_versions(records),
        max_severity=_text(group.get("max_severity")),
        summary=_summary(package.vulnerabilities.get(canonical) or records[0]),
    )


def _fallback_finding(
    package: _PackageInfo,
    advisory: str,
    vulnerability: dict[str, object],
) -> OsvFinding:
    aliases = set(_text_values(vulnerability.get("aliases")))
    aliases.discard(advisory)
    return OsvFinding(
        path=package.source.path,
        source_label=package.source.label,
        source_type=package.source.source_type,
        ecosystem=package.ecosystem,
        package=package.name,
        version=package.version,
        advisory=advisory,
        aliases=tuple(sorted(aliases)),
        fixed_versions=_fixed_versions((vulnerability,)),
        max_severity=None,
        summary=_summary(vulnerability),
    )


def _fixed_versions(
    vulnerabilities: tuple[dict[str, object], ...],
) -> tuple[str, ...]:
    events = chain.from_iterable(_fixed_events(vulnerability) for vulnerability in vulnerabilities)
    fixes = {_text(event.get("fixed")) for event in events}
    return tuple(sorted(fixed for fixed in fixes if fixed is not None))


def _fixed_events(vulnerability: dict[str, object]) -> tuple[dict[str, object], ...]:
    ranges = chain.from_iterable(
        payloads.json_objects(affected.get("ranges"))
        for affected in payloads.json_objects(vulnerability.get("affected"))
    )
    return tuple(
        chain.from_iterable(
            payloads.json_objects(value_range.get("events")) for value_range in ranges
        ),
    )


def _summary(vulnerability: dict[str, object] | None) -> str | None:
    if vulnerability is None:
        return None
    raw = _text(vulnerability.get("summary"))
    if raw is None:
        return None
    text = " ".join(raw.split())
    if len(text) <= OSV_SUMMARY_CHAR_LIMIT:
        return text
    prefix = text[: OSV_SUMMARY_CHAR_LIMIT - 3].rstrip()
    ellipsis = "..."
    return f"{prefix}{ellipsis}"


def _safe_source_path(value: object) -> tuple[str | None, str]:
    text = _text(value)
    if text is None:
        return (None, "<unknown source>")
    windows_path = PureWindowsPath(text)
    posix_path = PurePosixPath(text.replace("\\", "/"))
    filename = windows_path.name or posix_path.name or "<unknown source>"
    unsafe = any(
        (
            posix_path.is_absolute(),
            windows_path.is_absolute(),
            bool(windows_path.drive),
            ".." in posix_path.parts,
            posix_path.as_posix() == ".",
        ),
    )
    if unsafe:
        return (None, filename)
    normalized = posix_path.as_posix()
    return (normalized, normalized)


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _text_values(value: object) -> tuple[str, ...]:
    values = payloads.json_array(value) or []
    texts = (_text(item) for item in values)
    return tuple(text for text in texts if text is not None)


def _finding_sort_key(finding: OsvFinding) -> tuple[str, str, str, str, str]:
    return (
        finding.source_label,
        finding.ecosystem,
        finding.package,
        finding.version,
        finding.advisory,
    )


def _fact(check: str, finding: OsvFinding) -> dict[str, object]:
    return payloads.fact_payload(
        {
            "check": check,
            "path": finding.path,
            "symbol": finding.advisory,
            "message": format_osv_finding(finding),
            "severity": "error",
        },
    )
