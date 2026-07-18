"""Identity-aware member collection diffing for normalized contracts."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import cast

from agent_maintainer.contracts.baseline import canonical_json
from agent_maintainer.contracts.models import ContractError, ContractKind

MEMBER_LIST_IDENTITIES = {
    "arguments": "name",
    "attributes": "name",
    "commands": "path",
    "exports": "name",
    "fields": "name",
    "methods": "name",
    "options": "name",
    "parameters": "name",
}
ORDERED_MEMBER_LISTS = frozenset(("arguments", "parameters"))


@dataclass(frozen=True)
class SemanticDelta:
    """One unclassified exact change between normalized contract bodies."""

    operation: str
    path: str
    before: object | None
    after: object | None


type Recurse = Callable[
    [ContractKind, Mapping[str, object], Mapping[str, object], str],
    list[SemanticDelta],
]


@dataclass(frozen=True)
class DiffContext:
    """Traversal facts shared by one identity-bearing collection diff."""

    kind: ContractKind
    path: str
    recurse: Recurse


def is_member_list(key: str) -> bool:
    """Return whether a normalized array uses stable member identities."""

    return key in MEMBER_LIST_IDENTITIES


def diff_member_mapping(
    before: Mapping[str, object],
    after: Mapping[str, object],
    *,
    context: DiffContext,
) -> list[SemanticDelta]:
    """Diff a JSON Schema property map by property identity."""

    return _diff_indexed_members(
        context.kind,
        _object_members(before, label="properties"),
        _object_members(after, label="properties"),
        context=context,
        identity_key=None,
    )


def diff_member_list(
    collection: str,
    before: list[object],
    after: list[object],
    *,
    context: DiffContext,
) -> list[SemanticDelta]:
    """Diff a normalized member array by its configured identity field."""

    identity_key = MEMBER_LIST_IDENTITIES[collection]
    old_members, old_order = _index_member_list(before, identity_key=identity_key, label=collection)
    new_members, new_order = _index_member_list(after, identity_key=identity_key, label=collection)
    changes: list[SemanticDelta] = []
    order_changed = (
        collection in ORDERED_MEMBER_LISTS
        and set(old_order) == set(new_order)
        and old_order != new_order
    ) or (
        collection == "parameters"
        and _has_nontrailing_positional_addition(
            old_members,
            new_members,
            old_order=old_order,
            new_order=new_order,
        )
    )
    if order_changed:
        changes.append(
            SemanticDelta(
                "constraint-change",
                _pointer(context.path, "order"),
                old_order,
                new_order,
            )
        )
    changes.extend(
        _diff_indexed_members(
            context.kind,
            old_members,
            new_members,
            context=context,
            identity_key=identity_key,
        )
    )
    return changes


def _has_nontrailing_positional_addition(
    before: Mapping[str, dict[str, object]],
    after: Mapping[str, dict[str, object]],
    *,
    old_order: list[str],
    new_order: list[str],
) -> bool:
    if not set(old_order).issubset(new_order):
        return False
    positional_kinds = {"positional-only", "positional-or-keyword"}
    existing_positions = [
        new_order.index(name) for name in old_order if before[name].get("kind") in positional_kinds
    ]
    if not existing_positions:
        return False
    last_existing = max(existing_positions)
    return any(
        after[name].get("kind") in positional_kinds and new_order.index(name) < last_existing
        for name in set(new_order) - set(old_order)
    )


def _diff_indexed_members(
    kind: ContractKind,
    before: Mapping[str, dict[str, object]],
    after: Mapping[str, dict[str, object]],
    *,
    context: DiffContext,
    identity_key: str | None,
) -> list[SemanticDelta]:
    removed = set(before) - set(after)
    added = set(after) - set(before)
    renames = _infer_renames(before, after, removed=removed, added=added, identity_key=identity_key)
    changes: list[SemanticDelta] = []
    for old_name, new_name in renames:
        changes.append(
            SemanticDelta(
                "member-rename",
                _pointer(context.path, new_name),
                _rename_payload(before[old_name], old_name, identity_key),
                _rename_payload(after[new_name], new_name, identity_key),
            )
        )
        removed.remove(old_name)
        added.remove(new_name)
    for name in sorted(removed):
        changes.append(
            SemanticDelta("member-remove", _pointer(context.path, name), before[name], None)
        )
    for name in sorted(added):
        changes.append(SemanticDelta("member-add", _pointer(context.path, name), None, after[name]))
    for name in sorted(set(before) & set(after)):
        changes.extend(
            context.recurse(
                kind,
                before[name],
                after[name],
                _pointer(context.path, name),
            )
        )
    return changes


def _infer_renames(
    before: Mapping[str, dict[str, object]],
    after: Mapping[str, dict[str, object]],
    *,
    removed: set[str],
    added: set[str],
    identity_key: str | None,
) -> list[tuple[str, str]]:
    candidates: dict[str, list[str]] = {}
    for old_name in sorted(removed):
        signature = _member_signature(before[old_name], identity_key=identity_key)
        candidates[old_name] = [
            new_name
            for new_name in sorted(added)
            if _member_signature(after[new_name], identity_key=identity_key) == signature
        ]
    result: list[tuple[str, str]] = []
    for old_name, matches in candidates.items():
        if len(matches) != 1:
            continue
        new_name = matches[0]
        reverse_matches = [name for name, values in candidates.items() if new_name in values]
        if len(reverse_matches) == 1:
            result.append((old_name, new_name))
    return result


def _member_signature(member: Mapping[str, object], *, identity_key: str | None) -> str:
    ignored = {"aliases"}
    if identity_key is not None:
        ignored.add(identity_key)
    return canonical_json({key: value for key, value in member.items() if key not in ignored})


def _rename_payload(
    member: Mapping[str, object],
    name: str,
    identity_key: str | None,
) -> dict[str, object]:
    payload = dict(member)
    if identity_key is None or identity_key == "path":
        payload["name"] = name
    return payload


def _index_member_list(
    values: list[object],
    *,
    identity_key: str,
    label: str,
) -> tuple[dict[str, dict[str, object]], list[str]]:
    members: dict[str, dict[str, object]] = {}
    order: list[str] = []
    for value in values:
        if not isinstance(value, dict):
            raise ContractError(f"{label} member must be an object")
        member = cast(dict[str, object], value)
        identity = _member_identity(member.get(identity_key), label=label)
        if identity in members:
            raise ContractError(f"duplicate {label} member: {identity}")
        members[identity] = member
        order.append(identity)
    return members, order


def _member_identity(value: object | None, *, label: str) -> str:
    if isinstance(value, str) and value:
        return value
    if isinstance(value, list) and value:
        values = cast(list[object], value)
        if all(isinstance(item, str) and item for item in values):
            return "/".join(cast(list[str], values))
    raise ContractError(f"{label} member has no valid identity")


def _object_members(
    mapping: Mapping[str, object],
    *,
    label: str,
) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for name, value in mapping.items():
        if not isinstance(value, dict):
            raise ContractError(f"{label} member must be an object")
        result[name] = cast(dict[str, object], value)
    return result


def _pointer(path: str, part: str) -> str:
    encoded = part.replace("~", "~0").replace("/", "~1")
    return f"{path}/{encoded}"
