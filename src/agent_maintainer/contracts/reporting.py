"""Deterministic JSON and bounded human contract report rendering."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence

from agent_maintainer.contracts.limits import MAX_REPORT_ITEMS
from agent_maintainer.contracts.models import (
    ContractChange,
    ContractDecision,
    ContractObligation,
    ContractReport,
    Descriptor,
    RepairFact,
)

JsonItem = dict[str, object]


def report_to_dict(report: ContractReport) -> dict[str, object]:
    """Return the complete explicit version-one report schema."""

    return {
        "schema_version": report.schema_version,
        "mode": report.mode,
        "base_ref": report.base_ref,
        "base_available": report.base_available,
        "base_package_version": report.base_package_version,
        "current_package_version": report.current_package_version,
        "can_snapshot": report.can_snapshot,
        "unresolved": report.unresolved,
        "descriptors": [
            _descriptor(item)
            for item in sorted(report.descriptors, key=lambda value: value.contract_id)
        ],
        "changes": [
            _change(item)
            for item in sorted(report.changes, key=lambda value: value.identity())
        ],
        "obligations": [
            _obligation(item)
            for item in sorted(report.obligations, key=_obligation_key)
        ],
        "decisions": [
            _decision(item)
            for item in sorted(
                report.decisions,
                key=lambda value: (value.contract, value.fingerprint),
            )
        ],
        "repair_facts": [
            _repair_fact(item)
            for item in sorted(
                report.repair_facts,
                key=lambda value: (value.contract_id, value.fingerprint, value.summary),
            )
        ],
        "advisories": list(sorted(report.advisories)),
        "errors": list(sorted(report.errors)),
    }


def render_json(report: ContractReport) -> str:
    """Render complete stable ASCII JSON with one trailing newline."""

    return json.dumps(report_to_dict(report), ensure_ascii=True, indent=2) + "\n"


def render_text(report: ContractReport) -> str:
    """Render a bounded stable human report suitable for captured logs."""

    payload = report_to_dict(report)
    status = "INVALID" if report.errors else "BLOCKED" if report.unresolved else "CLEAN"
    lines = [
        f"Contract compatibility: {status}",
        f"Mode: {_escaped(report.mode)}",
        f"Base ref: {_escaped(report.base_ref or '(none)')}",
        f"Package: {_escaped(report.base_package_version or '(none)')} -> "
        f"{_escaped(report.current_package_version or '(none)')}",
    ]
    sections: tuple[tuple[str, Sequence[object]], ...] = (
        ("Contracts", _items(payload["descriptors"])),
        ("Changes", _items(payload["changes"])),
        ("Obligations", _items(payload["obligations"])),
        ("Decisions", _items(payload["decisions"])),
        ("Repair facts", _items(payload["repair_facts"])),
        ("Advisories", _items(payload["advisories"])),
        ("Errors", _items(payload["errors"])),
    )
    for title, items in sections:
        _append_section(lines, title, items, _human_item)
    return "\n".join(lines) + "\n"


def _descriptor(item: Descriptor) -> JsonItem:
    return {
        "contract_id": item.contract_id,
        "kind": item.kind,
        "owner": item.owner,
        "stability": item.stability,
        "revision": item.revision,
        "sources": list(item.sources),
        "body": item.body,
        "fingerprint": item.fingerprint,
    }


def _change(item: ContractChange) -> JsonItem:
    return {
        "contract_id": item.contract_id,
        "operation": item.operation,
        "path": item.path,
        "before": item.before,
        "after": item.after,
        "classification": item.classification,
        "fingerprint": item.fingerprint,
        "reason": item.reason,
    }


def _obligation(item: ContractObligation) -> JsonItem:
    return {
        "kind": item.kind,
        "status": item.status,
        "message": item.message,
        "contract_id": item.contract_id,
        "minimum_impact": item.minimum_impact,
        "current": item.current,
        "expected": item.expected,
        "fingerprints": list(item.fingerprints),
        "missing_paths": list(item.missing_paths),
    }


def _decision(item: ContractDecision) -> JsonItem:
    return {
        "contract": item.contract,
        "fingerprint": item.fingerprint,
        "classification": item.classification,
        "reason": item.reason,
    }


def _repair_fact(item: RepairFact) -> JsonItem:
    return {
        "kind": item.kind,
        "contract_id": item.contract_id,
        "fingerprint": item.fingerprint,
        "summary": item.summary,
        "inspect_command": item.inspect_command,
    }


def _obligation_key(item: ContractObligation) -> tuple[str, str, str, str, str]:
    return (item.contract_id, item.kind, item.status, item.current, item.expected)


def _items(value: object) -> Sequence[object]:
    if not isinstance(value, list):
        raise TypeError("report section must be a list")
    return value


def _append_section(
    lines: list[str],
    title: str,
    items: Sequence[object],
    render: Callable[[object], str],
) -> None:
    if not items:
        return
    lines.append(f"{title}:")
    lines.extend(f"- {render(item)}" for item in items[:MAX_REPORT_ITEMS])
    omitted = len(items) - MAX_REPORT_ITEMS
    if omitted > 0:
        lines.append(f"- ... {omitted} more; use --json")


def _human_item(value: object) -> str:
    if isinstance(value, str):
        return _escaped(value)
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _escaped(value: str) -> str:
    return json.dumps(value, ensure_ascii=True)[1:-1]
