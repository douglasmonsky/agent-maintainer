"""Pure input adapters for package-manager audit JSON projections."""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

from agent_repair_facts.parsers.typescript_audit_adapter_utils import (
    JsonObject,
    advisory_container,
    list_value,
    object_value,
    record_from_item,
    records_from_items,
    vulnerability_map,
)
from agent_repair_facts.parsers.typescript_package_manager_audit_contract import RawAuditRecord

Adapter = Callable[[object], tuple[RawAuditRecord, ...] | None]
UNSUPPORTED_RESULT: tuple[RawAuditRecord, ...] | None = cast(
    tuple[RawAuditRecord, ...] | None,
    None,
)


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

    return _parse_package_payload(payload, advisories_first=False)


def parse_pnpm_payload(payload: object) -> tuple[RawAuditRecord, ...] | None:
    """Parse pnpm advisory objects and supported wrapper projections."""

    return _parse_package_payload(payload, advisories_first=True)


def _parse_package_payload(
    payload: object,
    *,
    advisories_first: bool,
) -> tuple[RawAuditRecord, ...] | None:
    """Parse the shared npm/pnpm wrapper shapes."""

    items = list_value(payload)
    if items is not None:
        return records_from_items(items)
    root = object_value(payload)
    if root is None:
        return None
    parsers: tuple[tuple[str, Adapter], ...] = (
        (("advisories", advisory_container), ("vulnerabilities", vulnerability_map))
        if advisories_first
        else (
            ("vulnerabilities", vulnerability_map),
            ("advisories", advisory_container),
        )
    )
    clean_projection = any(key in root for key in ("metadata", "auditReportVersion", "actions"))
    for key, parser in parsers:
        value = root.get(key, None)
        if value is not None:
            return parser(value)
    return () if clean_projection else None


def parse_yarn_record(payload: object) -> tuple[RawAuditRecord, ...] | None:
    """Parse Yarn auditAdvisory NDJSON and object projections."""

    items = list_value(payload)
    if items is not None:
        return records_from_items(items)
    root = object_value(payload)
    if root is None:
        return None
    return _parse_yarn_object(root)


def _parse_yarn_object(root: JsonObject) -> tuple[RawAuditRecord, ...] | None:
    """Parse one Yarn object projection."""

    record_type = root.get("type", None)
    if record_type in {"auditSummary", "auditAction"}:
        return ()
    if record_type == "auditAdvisory":
        return _parse_yarn_advisory(root)
    advisories = root.get("advisories", None)
    if advisories is not None:
        return advisory_container(advisories)
    return () if any(key in root for key in ("auditReportVersion", "metadata")) else None


def _parse_yarn_advisory(root: JsonObject) -> tuple[RawAuditRecord, ...] | None:
    """Parse the nested Yarn auditAdvisory payload."""

    data = object_value(root.get("data", None)) or {}
    advisory = object_value(data.get("advisory", None)) or data
    record = record_from_item(advisory)
    if record is None:
        return None
    return (record,)


def parse_bun_payload(payload: object) -> tuple[RawAuditRecord, ...] | None:
    """Parse Bun advisory object/NDJSON projections without trusting chatter."""

    items = list_value(payload)
    if items is not None:
        return records_from_items(items)
    root = object_value(payload)
    if root is None:
        return None
    return _parse_bun_object(root)


def _parse_bun_object(root: JsonObject) -> tuple[RawAuditRecord, ...] | None:
    """Parse one Bun object projection."""

    for key, parser in (
        ("advisories", advisory_container),
        ("vulnerabilities", vulnerability_map),
    ):
        value = root.get(key, None)
        if value is not None:
            return parser(value)
    data = object_value(root.get("data", None))
    if data and any(data_key in data for data_key in ("advisory", "package", "module_name")):
        return _record_result(data.get("advisory", data))
    record = record_from_item(root)
    if record is not None:
        return (record,)
    return () if root.get("type", None) == "auditSummary" or "metadata" in root else None


def _record_result(value: object) -> tuple[RawAuditRecord, ...] | None:
    """Wrap one optional raw record in the adapter result shape."""

    record = record_from_item(value)
    if record is None:
        return None
    return (record,)


def _unsupported_payload(_payload: object) -> tuple[RawAuditRecord, ...] | None:
    """Return the adapter's unsupported result."""

    return UNSUPPORTED_RESULT
