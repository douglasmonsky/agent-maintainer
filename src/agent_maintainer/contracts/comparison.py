"""Deterministic comparison and classification of normalized contract descriptors."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast

from agent_maintainer.contracts.baseline import fingerprint
from agent_maintainer.contracts.classifiers import classify_change
from agent_maintainer.contracts.diffing import (
    DiffContext,
    SemanticDelta,
    diff_member_list,
    diff_member_mapping,
    is_member_list,
)
from agent_maintainer.contracts.models import (
    ContractChange,
    ContractDecision,
    ContractError,
    ContractKind,
    Descriptor,
)

ATOMIC_MAPPINGS = frozenset(("const", "default", "value"))


def change_fingerprint(
    contract_id: str,
    operation: str,
    path: str,
    before: object | None,
    after: object | None,
) -> str:
    """Return an exact fingerprint independent of classification or rationale."""

    return fingerprint(
        {
            "after": after,
            "before": before,
            "contract_id": contract_id,
            "operation": operation,
            "path": path,
        }
    )


def compare_descriptors(
    base: Sequence[Descriptor],
    current: Sequence[Descriptor],
    decisions: Sequence[ContractDecision],
) -> tuple[ContractChange, ...]:
    """Compare two descriptor sets and apply exact review decisions."""

    base_by_id = _descriptor_index(base, label="base")
    current_by_id = _descriptor_index(current, label="current")
    decision_index = {(item.contract, item.fingerprint): item for item in decisions}
    changes: list[ContractChange] = []
    for contract_id in sorted(set(base_by_id) | set(current_by_id)):
        before = base_by_id.get(contract_id)
        after = current_by_id.get(contract_id)
        kind, deltas = _descriptor_deltas(before, after)
        changes.extend(_materialize(contract_id, kind, delta, decision_index) for delta in deltas)
    return tuple(
        sorted(
            changes,
            key=lambda item: (item.contract_id, item.path, item.operation, item.fingerprint),
        )
    )


def _descriptor_deltas(
    before: Descriptor | None,
    after: Descriptor | None,
) -> tuple[ContractKind, tuple[SemanticDelta, ...]]:
    if before is None:
        if after is None:
            raise ContractError("descriptor identity index is inconsistent")
        return after.kind, (SemanticDelta("contract-add", "/", None, after.body),)
    if after is None:
        return before.kind, (SemanticDelta("contract-remove", "/", before.body, None),)
    if before.kind == after.kind:
        deltas = tuple(_diff_mapping(before.kind, before.body, after.body, ""))
        return before.kind, deltas
    return after.kind, (SemanticDelta("type-change", "/kind", before.kind, after.kind),)


def _descriptor_index(
    descriptors: Sequence[Descriptor],
    *,
    label: str,
) -> dict[str, Descriptor]:
    result: dict[str, Descriptor] = {}
    for descriptor in descriptors:
        if descriptor.contract_id in result:
            raise ContractError(f"duplicate {label} descriptor: {descriptor.contract_id}")
        result[descriptor.contract_id] = descriptor
    return result


def _materialize(
    contract_id: str,
    kind: ContractKind,
    delta: SemanticDelta,
    decisions: Mapping[tuple[str, str], ContractDecision],
) -> ContractChange:
    exact_fingerprint = change_fingerprint(
        contract_id,
        delta.operation,
        delta.path,
        delta.before,
        delta.after,
    )
    classification, reason = classify_change(
        kind,
        delta.operation,
        delta.path,
        delta.before,
        delta.after,
    )
    decision = decisions.get((contract_id, exact_fingerprint))
    if classification == "review-required" and decision is not None:
        classification = decision.classification
        reason = decision.reason
    return ContractChange(
        contract_id=contract_id,
        operation=delta.operation,
        path=delta.path,
        before=delta.before,
        after=delta.after,
        classification=classification,
        fingerprint=exact_fingerprint,
        reason=reason,
    )


def _diff_mapping(
    kind: ContractKind,
    before: Mapping[str, object],
    after: Mapping[str, object],
    path: str,
) -> list[SemanticDelta]:
    changes: list[SemanticDelta] = []
    for key in sorted(set(before) | set(after)):
        old = before.get(key)
        new = after.get(key)
        if key in before and key in after and old == new:
            continue
        changes.extend(
            _diff_value(
                kind,
                key,
                old if key in before else None,
                new if key in after else None,
                path=_pointer(path, key),
            )
        )
    return changes


def _diff_value(
    kind: ContractKind,
    key: str,
    before: object | None,
    after: object | None,
    *,
    path: str,
) -> list[SemanticDelta]:
    if key == "properties":
        return diff_member_mapping(
            _mapping_or_empty(before, label="properties"),
            _mapping_or_empty(after, label="properties"),
            context=DiffContext(kind=kind, path=path, recurse=_diff_mapping),
        )
    if is_member_list(key):
        return diff_member_list(
            key,
            _list_or_empty(before, label=key),
            _list_or_empty(after, label=key),
            context=DiffContext(kind=kind, path=path, recurse=_diff_mapping),
        )
    if key not in ATOMIC_MAPPINGS and isinstance(before, dict) and isinstance(after, dict):
        return _diff_mapping(
            kind,
            cast(dict[str, object], before),
            cast(dict[str, object], after),
            path,
        )
    return [
        SemanticDelta(
            _leaf_operation(key),
            path,
            cast(object | None, before),
            after,
        )
    ]


def _mapping_or_empty(value: object | None, *, label: str) -> Mapping[str, object]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be an object")
    return cast(Mapping[str, object], value)


def _list_or_empty(value: object | None, *, label: str) -> list[object]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ContractError(f"{label} must be an array")
    return cast(list[object], value)


def _leaf_operation(key: str) -> str:
    operations = {
        "aliases": "alias-change",
        "default": "default-change",
        "has_default": "default-change",
        "required": "requiredness-change",
        "unsupported_semantics": "unsupported-semantic-change",
    }
    if key in {"annotation", "kind", "return_annotation", "type", "types"}:
        return "type-change"
    return operations.get(key, "constraint-change")


def _pointer(path: str, part: str) -> str:
    encoded = part.replace("~", "~0").replace("/", "~1")
    return f"{path}/{encoded}"
