"""Kind-aware classification of exact semantic contract changes."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from agent_maintainer.contracts import member_rules
from agent_maintainer.contracts.baseline import canonical_json
from agent_maintainer.contracts.models import (
    BREAKING,
    COMPATIBLE,
    REVIEW_REQUIRED,
    Classification,
    ContractKind,
)

ClassificationResult = tuple[Classification, str]


def classify_change(
    kind: ContractKind,
    operation: str,
    path: str,
    before: object | None,
    after: object | None,
) -> ClassificationResult:
    """Classify one normalized operation using conservative compatibility rules."""

    return _classify_primary(kind, operation, path, before, after)


def _classify_primary(
    kind: ContractKind,
    operation: str,
    path: str,
    before: object | None,
    after: object | None,
) -> ClassificationResult:
    match operation:
        case "alias-change":
            result = _classify_aliases(before, after)
        case "constraint-change":
            result = _classify_constraint(kind, path, before, after)
        case "contract-add":
            result = (COMPATIBLE, "new contract surface")
        case "contract-remove" | "member-remove":
            result = (BREAKING, "contract surface removed")
        case "default-change":
            result = _classify_default(kind, path, before, after)
        case "member-add":
            result = _classify_member_add(kind, path, after)
        case _:
            result = _classify_secondary(kind, operation, path, before, after)
    return result


def _classify_secondary(
    _kind: ContractKind,
    operation: str,
    path: str,
    before: object | None,
    after: object | None,
) -> ClassificationResult:
    match operation:
        case "member-rename":
            return _classify_rename(before, after)
        case "requiredness-change":
            return _classify_requiredness(before, after)
        case "type-change":
            return _classify_type(path, before, after)
        case "unsupported-semantic-change":
            return REVIEW_REQUIRED, "unsupported semantics changed"
        case _:
            return REVIEW_REQUIRED, "unrecognized semantic operation"


def _classify_member_add(
    kind: ContractKind,
    path: str,
    after: object | None,
) -> ClassificationResult:
    member = _mapping(after)
    return member_rules.classify_member_add(kind, path, member)


def _classify_rename(
    before: object | None,
    after: object | None,
) -> tuple[Classification, str]:
    old_name = _mapping(before).get("name")
    aliases = _string_set(_mapping(after).get("aliases"))
    if isinstance(old_name, str) and old_name in aliases:
        return COMPATIBLE, "renamed member preserves its previous name as an alias"
    return REVIEW_REQUIRED, "inferred member rename has no proved alias mapping"


def _classify_type(
    path: str,
    before: object | None,
    after: object | None,
) -> tuple[Classification, str]:
    if path.endswith(("/annotation", "/return_annotation")):
        return REVIEW_REQUIRED, "annotation compatibility is not provable"
    before_types = _string_set(before)
    after_types = _string_set(after)
    if before_types and after_types:
        if before_types < after_types:
            return COMPATIBLE, "accepted type set widened"
        if after_types < before_types or before_types != after_types:
            return BREAKING, "accepted type set narrowed or changed incompatibly"
    return BREAKING, "value kind changed incompatibly"


def _classify_requiredness(
    before: object | None,
    after: object | None,
) -> tuple[Classification, str]:
    if before is False and after is True:
        return BREAKING, "optional member became required"
    if before is True and after is False:
        return COMPATIBLE, "required member became optional"
    return REVIEW_REQUIRED, "requiredness change is ambiguous"


def _classify_default(
    kind: ContractKind,
    path: str,
    before: object | None,
    after: object | None,
) -> tuple[Classification, str]:
    if path.endswith("/has_default"):
        if before is False and after is True:
            return COMPATIBLE, "parameter gained a default"
        if before is True and after is False:
            return BREAKING, "parameter lost its default"
    if kind in {"config-capabilities", "cli-manifest"}:
        return BREAKING, "public default changed"
    return REVIEW_REQUIRED, "literal default compatibility is not provable"


def _classify_aliases(
    before: object | None,
    after: object | None,
) -> tuple[Classification, str]:
    old = _string_set(before)
    new = _string_set(after)
    if old < new:
        return COMPATIBLE, "new alias preserves canonical identity"
    if new < old:
        return BREAKING, "supported alias removed"
    return REVIEW_REQUIRED, "aliases changed incompatibly or conflict"


def _classify_constraint(
    kind: ContractKind,
    path: str,
    before: object | None,
    after: object | None,
) -> ClassificationResult:
    key = path.rsplit("/", 1)[-1]
    constraint_handlers = {
        "additional_properties": _classify_additional_properties,
        "choices": _classify_enum,
        "const": _classify_incompatible_constraint,
        "enum": _classify_enum,
        "maximum_exclusive": _classify_exclusive,
        "minimum_exclusive": _classify_exclusive,
        "order": _classify_order,
        "pattern": _classify_incompatible_constraint,
    }
    handler = constraint_handlers.get(key)
    if handler is not None:
        return handler(before, after)
    bound_directions = {
        "exclusive_maximum": False,
        "exclusive_minimum": True,
        "max_items": False,
        "max_length": False,
        "maximum": False,
        "min_items": True,
        "min_length": True,
        "minimum": True,
    }
    bound_direction = bound_directions.get(key)
    if bound_direction is not None:
        return _classify_bound(before, after, tighter_when_higher=bound_direction)
    if key == "constraints" and isinstance(before, dict) and isinstance(after, dict):
        return _classify_constraint_mapping(
            kind,
            path,
            cast(dict[str, object], before),
            cast(dict[str, object], after),
        )
    if key == "value" and kind == "python-api":
        return REVIEW_REQUIRED, "exported literal compatibility is not provable"
    return REVIEW_REQUIRED, "constraint compatibility is not provable"


def _classify_order(_before: object | None, _after: object | None) -> ClassificationResult:
    return BREAKING, "positional member order changed"


def _classify_additional_properties(
    before: object | None,
    after: object | None,
) -> ClassificationResult:
    if before in {None, True} and after is False:
        return BREAKING, "additional properties are no longer accepted"
    if before is False and after is True:
        return COMPATIBLE, "additional properties are now accepted"
    return REVIEW_REQUIRED, "additional-property compatibility is not provable"


def _classify_exclusive(
    before: object | None,
    after: object | None,
) -> ClassificationResult:
    if before is False and after is True:
        return BREAKING, "constraint became exclusive"
    if before is True and after is False:
        return COMPATIBLE, "exclusive constraint was relaxed"
    return REVIEW_REQUIRED, "constraint exclusivity is not provable"


def _classify_incompatible_constraint(
    _before: object | None,
    _after: object | None,
) -> ClassificationResult:
    return BREAKING, "accepted values changed incompatibly"


def _classify_enum(
    before: object | None,
    after: object | None,
) -> tuple[Classification, str]:
    old = _json_set(before)
    new = _json_set(after)
    if old < new:
        return REVIEW_REQUIRED, "enum expanded for potentially exhaustive consumers"
    if new < old:
        return BREAKING, "accepted enum values were removed"
    return REVIEW_REQUIRED, "enum values changed incompatibly"


def _classify_bound(
    before: object | None,
    after: object | None,
    *,
    tighter_when_higher: bool,
) -> tuple[Classification, str]:
    if isinstance(before, (int, float)) and isinstance(after, (int, float)):
        tightened = after > before if tighter_when_higher else after < before
        if tightened:
            return BREAKING, "accepted range narrowed"
        return COMPATIBLE, "accepted range widened"
    if before is None and after is not None:
        return BREAKING, "new range constraint narrows accepted values"
    if before is not None and after is None:
        return COMPATIBLE, "range constraint was removed"
    return REVIEW_REQUIRED, "range compatibility is not provable"


def _classify_constraint_mapping(
    kind: ContractKind,
    path: str,
    before: dict[str, object],
    after: dict[str, object],
) -> tuple[Classification, str]:
    results = [
        _classify_constraint(kind, f"{path}/{key}", before.get(key), after.get(key))[0]
        for key in sorted(set(before) | set(after))
        if before.get(key) != after.get(key)
    ]
    if BREAKING in results:
        return BREAKING, "one or more accepted-value constraints tightened"
    if REVIEW_REQUIRED in results:
        return REVIEW_REQUIRED, "one or more constraint changes require review"
    return COMPATIBLE, "accepted-value constraints were relaxed"


def _mapping(value: object | None) -> Mapping[str, object]:
    if isinstance(value, dict):
        return cast(Mapping[str, object], value)
    return {}


def _string_set(value: object | None) -> set[str]:
    if isinstance(value, str):
        return {value}
    if not isinstance(value, (list, tuple)):
        return set()
    values = cast(list[object] | tuple[object, ...], value)
    return {item for item in values if isinstance(item, str)}


def _json_set(value: object | None) -> set[str]:
    if not isinstance(value, (list, tuple)):
        return set()
    values = cast(list[object] | tuple[object, ...], value)
    return {canonical_json(item) for item in values}
