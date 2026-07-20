"""Shared JSON shape helpers for package-manager audit adapters."""

from __future__ import annotations

from typing import cast

from agent_repair_facts.parsers.typescript_package_manager_audit_contract import RawAuditRecord

JsonObject = dict[str, object]


def records_from_items(items: list[object]) -> tuple[RawAuditRecord, ...]:
    """Parse a list of record projections."""

    return tuple(record for item in items if (record := record_from_item(item)) is not None)


def vulnerability_map(value: object) -> tuple[RawAuditRecord, ...] | None:
    """Parse npm's package-keyed vulnerability map."""

    mapping = object_value(value)
    if mapping is None:
        if value:
            return None
        return ()
    return tuple(
        record
        for package, details in mapping.items()
        if (record := record_from_vulnerability(package, details)) is not None
    )


def advisory_container(value: object) -> tuple[RawAuditRecord, ...] | None:
    """Parse a list or map of advisory records."""

    items = list_value(value)
    if items is not None:
        return records_from_items(items)
    mapping = object_value(value)
    if mapping is None:
        if value:
            return None
        return ()
    return tuple(
        record
        for advisory_id, details in mapping.items()
        if (record := record_from_item(details, fallback_advisory_id=advisory_id)) is not None
    )


def record_from_vulnerability(package: str, details: object) -> RawAuditRecord | None:
    """Normalize one npm vulnerability entry."""

    value = object_value(details)
    if value is None:
        return None
    advisory_ids = vulnerability_advisory_ids(value)
    if not advisory_ids:
        return None
    return RawAuditRecord(
        package=package or first(value, "name", "package", "module_name"),
        severity=first(value, "severity", "level"),
        advisory_ids=advisory_ids,
        vulnerable_ranges=values(
            first(value, "range", "vulnerable_versions", "vulnerableVersions")
        ),
        fixed_versions=fixed_versions(value),
        scope=scope(value),
        directness=directness(value),
        path=first_path(value),
        title=first(value, "title", "summary"),
    )


def vulnerability_advisory_ids(value: JsonObject) -> tuple[object, ...]:
    """Extract advisory IDs from npm's mixed ``via`` projection."""

    via = value.get("via", None)
    via_values = list_value(via) or (via,)
    mapping_ids = tuple(
        candidate
        for item in via_values
        if (mapping_item := object_value(item)) is not None
        for candidate in (first(mapping_item, "source", "id", "advisoryId"),)
        if looks_like_id(candidate)
    )
    scalar_ids = tuple(
        item for item in via_values if looks_like_id(item) and object_value(item) is None
    )
    return mapping_ids + scalar_ids


def record_from_item(item: object, fallback_advisory_id: object = "") -> RawAuditRecord | None:
    """Normalize one generic advisory object."""

    value = object_value(item)
    if value is None:
        return None
    package = first(value, "package", "packageName", "module_name", "module", "name")
    advisory_ids = id_values(value)
    if fallback_advisory_id:
        advisory_ids = (*advisory_ids, fallback_advisory_id)
    if not advisory_ids:
        return None
    finding_values = list_value(value.get("findings", None)) or ()
    finding_paths = tuple(
        path
        for finding in finding_values
        if (finding_object := object_value(finding)) is not None
        for path in values(first(finding_object, "paths", "path", "node"))
    )
    return RawAuditRecord(
        package=package,
        severity=first(value, "severity", "level"),
        advisory_ids=advisory_ids,
        vulnerable_ranges=values(
            first(value, "vulnerable_versions", "vulnerableVersions", "range", "vulnerableRange")
        ),
        fixed_versions=fixed_versions(value),
        scope=scope(value),
        directness=directness(value),
        path=finding_paths[0] if finding_paths else first_path(value),
        title=first(value, "title", "summary"),
    )


def id_values(value: JsonObject) -> tuple[object, ...]:
    """Return explicit advisory IDs from an object."""

    ids: list[object] = []
    for key in ("id", "source", "advisory", "advisoryId", "githubAdvisoryId"):
        candidate = value.get(key, None)
        if looks_like_id(candidate):
            ids.append(candidate)
    return tuple(ids)


def fixed_versions(value: JsonObject) -> tuple[object, ...]:
    """Return explicit fix versions, never an inferred package update."""

    versions = list(
        values(
            first(value, "patched_versions", "patchedVersions", "fixed_versions", "fixedVersions")
        )
    )
    fix = object_value(value.get("fixAvailable", None))
    if fix is not None:
        version = first(fix, "version", "fixedVersion")
        if version:
            versions.append(version)
    return tuple(versions)


def scope(value: JsonObject) -> object:
    """Return explicit dependency scope."""

    explicit = first(value, "scope", "dependencyScope", "scopeType")
    if explicit:
        return explicit
    for key, selected in (("dev", "dev"), ("optional", "optional"), ("peer", "peer")):
        if value.get(key, None) is True:
            return selected
    return ""


def directness(value: JsonObject) -> object:
    """Return explicit dependency directness."""

    explicit = first(value, "directness", "dependencyType")
    if explicit:
        return explicit
    is_direct = value.get("isDirect", None)
    if isinstance(is_direct, bool):
        return "direct" if is_direct else "indirect"
    return ""


def first_path(value: JsonObject) -> object:
    """Return the first explicitly reported dependency path."""

    paths = values(first(value, "paths", "nodes", "path"))
    return paths[0] if paths else ""


def values(value: object) -> tuple[object, ...]:
    """Normalize a scalar or sequence to a tuple."""

    if value is None:
        return ()
    if isinstance(value, list):
        return tuple(cast(list[object], value))
    if isinstance(value, tuple):
        return tuple(cast(tuple[object, ...], value))
    return (value,)


def first(value: JsonObject, *keys: str) -> object:
    """Return the first present value for an ordered key list."""

    for key in keys:
        candidate = value.get(key, None)
        if candidate is not None:
            return candidate
    return ""


def object_value(value: object) -> JsonObject | None:
    """Normalize one JSON object and reject non-text keys."""

    if not isinstance(value, dict):
        return None
    normalized: JsonObject = {}
    for key, item in cast(dict[object, object], value).items():
        if not isinstance(key, str):
            return None
        normalized[key] = item
    return normalized


def list_value(value: object) -> list[object] | None:
    """Normalize one JSON list to object items."""

    return cast(list[object], value) if isinstance(value, list) else None


def looks_like_id(value: object) -> bool:
    """Return whether a value has a recognized advisory identifier shape."""

    if isinstance(value, int) and not isinstance(value, bool):
        return True
    if not isinstance(value, str) or not value.strip():
        return False
    normalized = value.strip().upper()
    return normalized.startswith(("GHSA-", "CVE-", "OSV-", "NPM-")) or normalized.isdigit()
