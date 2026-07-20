"""Pure input adapters for package-manager audit JSON projections."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from agent_repair_facts.parsers.typescript_package_manager_audit import RawAuditRecord

JsonObject = dict[str, object]
Adapter = Callable[[object], tuple[RawAuditRecord, ...] | None]


def adapter_for(manager: str) -> Adapter:
    """Return the adapter selected by explicit configuration."""

    return {
        "npm": parse_npm_payload,
        "pnpm": parse_pnpm_payload,
        "yarn": parse_yarn_record,
        "bun": parse_bun_payload,
    }.get(manager, _unsupported_payload)


def parse_npm_payload(payload: object) -> tuple[RawAuditRecord, ...] | None:
    """Parse current or legacy npm audit object projections."""

    if isinstance(payload, list):
        return tuple(record for item in payload if (record := _record_from_item(item)) is not None)
    root = _object(payload)
    if root is None:
        return None
    if "vulnerabilities" in root:
        return _vulnerability_map(root["vulnerabilities"])
    if "advisories" in root:
        return _advisory_container(root["advisories"])
    if "auditReportVersion" in root or "metadata" in root:
        return ()
    return None


def parse_pnpm_payload(payload: object) -> tuple[RawAuditRecord, ...] | None:
    """Parse pnpm advisory objects and supported wrapper projections."""

    if isinstance(payload, list):
        return tuple(record for item in payload if (record := _record_from_item(item)) is not None)
    root = _object(payload)
    if root is None:
        return None
    if "advisories" in root:
        return _advisory_container(root["advisories"])
    if "vulnerabilities" in root:
        return _vulnerability_map(root["vulnerabilities"])
    if any(key in root for key in ("metadata", "auditReportVersion", "actions")):
        return ()
    return None


def parse_yarn_record(payload: object) -> tuple[RawAuditRecord, ...] | None:
    """Parse Yarn auditAdvisory NDJSON and object projections."""

    result: tuple[RawAuditRecord, ...] | None = None
    root = _object(payload)
    if root is None and isinstance(payload, list):
        result = tuple(
            record for item in payload if (record := _record_from_item(item)) is not None
        )
    elif root is not None:
        record_type = root.get("type")
        if record_type in {"auditSummary", "auditAction"}:
            result = ()
        elif record_type == "auditAdvisory":
            data = _object(root.get("data")) or {}
            advisory = _object(data.get("advisory")) or data
            record = _record_from_item(advisory)
            result = (record,) if record is not None else None
        elif "advisories" in root:
            result = _advisory_container(root["advisories"])
        elif "auditReportVersion" in root or "metadata" in root:
            result = ()
    return result


def parse_bun_payload(payload: object) -> tuple[RawAuditRecord, ...] | None:
    """Parse Bun advisory object/NDJSON projections without trusting chatter."""

    result: tuple[RawAuditRecord, ...] | None = None
    if isinstance(payload, list):
        result = tuple(
            record for item in payload if (record := _record_from_item(item)) is not None
        )
    else:
        root = _object(payload)
        if root is not None:
            if "advisories" in root:
                result = _advisory_container(root["advisories"])
            elif "vulnerabilities" in root:
                result = _vulnerability_map(root["vulnerabilities"])
            else:
                data = _object(root.get("data"))
                if data is not None and any(
                    key in data for key in ("advisory", "package", "module_name")
                ):
                    record = _record_from_item(data.get("advisory", data))
                    result = (record,) if record is not None else None
                else:
                    record = _record_from_item(root)
                    if record is not None:
                        result = (record,)
                    elif root.get("type") == "auditSummary" or "metadata" in root:
                        result = ()
    return result


def _vulnerability_map(value: object) -> tuple[RawAuditRecord, ...] | None:
    mapping = _object(value)
    if mapping is None:
        return () if value == {} else None
    return tuple(
        record
        for package, details in mapping.items()
        if (record := _record_from_vulnerability(package, details)) is not None
    )


def _advisory_container(value: object) -> tuple[RawAuditRecord, ...] | None:
    if isinstance(value, list):
        return tuple(record for item in value if (record := _record_from_item(item)) is not None)
    mapping = _object(value)
    if mapping is None:
        return () if value == {} else None
    return tuple(
        record
        for advisory_id, details in mapping.items()
        if (record := _record_from_item(details, fallback_advisory_id=advisory_id)) is not None
    )


def _record_from_vulnerability(package: str, details: object) -> RawAuditRecord | None:
    value = _object(details)
    if value is None:
        return None
    via = value.get("via")
    via_values = via if isinstance(via, list) else (via,)
    advisory_ids = tuple(
        item
        for item in via_values
        if isinstance(item, Mapping)
        for item in (_first(item, "source", "id", "advisoryId"),)
        if _looks_like_id(item)
    )
    advisory_ids += tuple(
        item for item in via_values if _looks_like_id(item) and not isinstance(item, Mapping)
    )
    if not advisory_ids:
        return None
    return RawAuditRecord(
        package=package or _first(value, "name", "package", "module_name"),
        severity=_first(value, "severity", "level"),
        advisory_ids=advisory_ids,
        vulnerable_ranges=_values(
            _first(value, "range", "vulnerable_versions", "vulnerableVersions")
        ),
        fixed_versions=_fixed_versions(value),
        scope=_scope(value),
        directness=_directness(value),
        path=_first_path(value),
        title=_first(value, "title", "summary"),
    )


def _record_from_item(item: object, fallback_advisory_id: object = "") -> RawAuditRecord | None:
    value = _object(item)
    if value is None:
        return None
    package = _first(value, "package", "packageName", "module_name", "module", "name")
    advisory_ids = _id_values(value)
    if fallback_advisory_id:
        advisory_ids = (*advisory_ids, fallback_advisory_id)
    if not advisory_ids:
        return None
    findings = value.get("findings")
    finding_values = findings if isinstance(findings, list) else ()
    finding_paths = tuple(
        path
        for finding in finding_values
        if isinstance(finding, Mapping)
        for path in _values(_first(finding, "paths", "path", "node"))
    )
    return RawAuditRecord(
        package=package,
        severity=_first(value, "severity", "level"),
        advisory_ids=advisory_ids,
        vulnerable_ranges=_values(
            _first(value, "vulnerable_versions", "vulnerableVersions", "range", "vulnerableRange")
        ),
        fixed_versions=_fixed_versions(value),
        scope=_scope(value),
        directness=_directness(value),
        path=finding_paths[0] if finding_paths else _first_path(value),
        title=_first(value, "title", "summary"),
    )


def _id_values(value: JsonObject) -> tuple[object, ...]:
    """Return explicit advisory IDs from an object."""

    ids: list[object] = []
    for key in ("id", "source", "advisory", "advisoryId", "githubAdvisoryId"):
        candidate = value.get(key)
        if _looks_like_id(candidate):
            ids.append(candidate)
    return tuple(ids)


def _fixed_versions(value: JsonObject) -> tuple[object, ...]:
    """Return explicit fix versions, never an inferred package update."""

    versions = list(
        _values(
            _first(value, "patched_versions", "patchedVersions", "fixed_versions", "fixedVersions")
        )
    )
    fix = _object(value.get("fixAvailable"))
    if fix is not None:
        version = _first(fix, "version", "fixedVersion")
        if version:
            versions.append(version)
    return tuple(versions)


def _scope(value: JsonObject) -> object:
    explicit = _first(value, "scope", "dependencyScope", "scopeType")
    if explicit:
        return explicit
    for key, scope in (("dev", "dev"), ("optional", "optional"), ("peer", "peer")):
        if value.get(key) is True:
            return scope
    return ""


def _directness(value: JsonObject) -> object:
    explicit = _first(value, "directness", "dependencyType")
    if explicit:
        return explicit
    is_direct = value.get("isDirect")
    if isinstance(is_direct, bool):
        return "direct" if is_direct else "indirect"
    return ""


def _first_path(value: JsonObject) -> object:
    paths = _values(_first(value, "paths", "nodes", "path"))
    return paths[0] if paths else ""


def _values(value: object) -> tuple[object, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(value)
    return (value,)


def _first(value: Mapping[str, object], *keys: str) -> object:
    for key in keys:
        candidate = value.get(key)
        if candidate is not None:
            return candidate
    return ""


def _object(value: object) -> JsonObject | None:
    return value if isinstance(value, dict) and all(isinstance(key, str) for key in value) else None


def _looks_like_id(value: object) -> bool:
    if isinstance(value, int) and not isinstance(value, bool):
        return True
    if not isinstance(value, str) or not value.strip():
        return False
    normalized = value.strip().upper()
    return normalized.startswith(("GHSA-", "CVE-", "OSV-", "NPM-")) or normalized.isdigit()


def _unsupported_payload(_payload: object) -> None:
    return None
