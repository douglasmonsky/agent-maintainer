"""Kind-aware classification of exact semantic contract changes."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import cast

from agent_maintainer.contracts.baseline import canonical_json
from agent_maintainer.contracts.models import Classification, ContractKind

LOWER_BOUNDS = frozenset(("exclusive_minimum", "min_items", "min_length", "minimum"))
UPPER_BOUNDS = frozenset(("exclusive_maximum", "max_items", "max_length", "maximum"))
type ClassificationResult = tuple[Classification, str]
type Classifier = Callable[
    [ContractKind, str, object | None, object | None],
    ClassificationResult,
]


def classify_change(
    kind: ContractKind,
    operation: str,
    path: str,
    before: object | None,
    after: object | None,
) -> ClassificationResult:
    """Classify one normalized operation using conservative compatibility rules."""

    handler = OPERATION_CLASSIFIERS.get(operation, _classify_unknown)
    return handler(kind, path, before, after)


def _classify_member_add(
    kind: ContractKind,
    path: str,
    after: object | None,
) -> ClassificationResult:
    member = _mapping(after)
    handler = MEMBER_ADD_CLASSIFIERS.get(kind, _classify_unknown_member_add)
    return handler(path, member)


def _classify_config_member_add(
    _path: str,
    member: Mapping[str, object],
) -> ClassificationResult:
    if member.get("required") is True:
        return "breaking", "new required configuration field"
    if "default" in member:
        return "compatible", "new optional configuration field with default"
    return "review-required", "new optional configuration field has no explicit default"


def _classify_cli_member_add(
    path: str,
    member: Mapping[str, object],
) -> ClassificationResult:
    if "/options/" not in path and "/arguments/" not in path:
        return "compatible", "new command surface"
    if member.get("required") is True:
        return "breaking", "new required command input"
    return "compatible", "new optional command input"


def _classify_python_member_add(
    path: str,
    member: Mapping[str, object],
) -> ClassificationResult:
    if "/parameters/" not in path:
        return "compatible", "new nominated Python API member"
    parameter_kind = member.get("kind")
    optional = member.get("has_default") is True or parameter_kind in {
        "var-keyword",
        "var-positional",
    }
    if optional:
        return "compatible", "new optional Python parameter"
    return "breaking", "new required Python parameter"


def _classify_schema_member_add(
    _path: str,
    member: Mapping[str, object],
) -> ClassificationResult:
    if member.get("required") is True:
        return "breaking", "new required schema property"
    return "compatible", "new optional schema property"


def _classify_unknown_member_add(
    _path: str,
    _member: Mapping[str, object],
) -> ClassificationResult:
    return "review-required", "new member requires review"


def _classify_rename(
    before: object | None,
    after: object | None,
) -> tuple[Classification, str]:
    old_name = _mapping(before).get("name")
    aliases = _string_set(_mapping(after).get("aliases"))
    if isinstance(old_name, str) and old_name in aliases:
        return "compatible", "renamed member preserves its previous name as an alias"
    return "review-required", "inferred member rename has no proved alias mapping"


def _classify_type(
    path: str,
    before: object | None,
    after: object | None,
) -> tuple[Classification, str]:
    if path.endswith(("/annotation", "/return_annotation")):
        return "review-required", "annotation compatibility is not provable"
    before_types = _string_set(before)
    after_types = _string_set(after)
    if before_types and after_types:
        if before_types < after_types:
            return "compatible", "accepted type set widened"
        if after_types < before_types or before_types != after_types:
            return "breaking", "accepted type set narrowed or changed incompatibly"
    return "breaking", "value kind changed incompatibly"


def _classify_requiredness(
    before: object | None,
    after: object | None,
) -> tuple[Classification, str]:
    if before is False and after is True:
        return "breaking", "optional member became required"
    if before is True and after is False:
        return "compatible", "required member became optional"
    return "review-required", "requiredness change is ambiguous"


def _classify_default(
    kind: ContractKind,
    path: str,
    before: object | None,
    after: object | None,
) -> tuple[Classification, str]:
    if path.endswith("/has_default"):
        if before is False and after is True:
            return "compatible", "parameter gained a default"
        if before is True and after is False:
            return "breaking", "parameter lost its default"
    if kind in {"config-capabilities", "cli-manifest"}:
        return "breaking", "public default changed"
    return "review-required", "literal default compatibility is not provable"


def _classify_aliases(
    before: object | None,
    after: object | None,
) -> tuple[Classification, str]:
    old = _string_set(before)
    new = _string_set(after)
    if old < new:
        return "compatible", "new alias preserves canonical identity"
    if new < old:
        return "breaking", "supported alias removed"
    return "review-required", "aliases changed incompatibly or conflict"


def _classify_constraint(
    kind: ContractKind,
    path: str,
    before: object | None,
    after: object | None,
) -> ClassificationResult:
    key = path.rsplit("/", 1)[-1]
    handler = CONSTRAINT_CLASSIFIERS.get(key)
    if handler is not None:
        return handler(before, after)
    if key in LOWER_BOUNDS:
        return _classify_bound(before, after, tighter_when_higher=True)
    if key in UPPER_BOUNDS:
        return _classify_bound(before, after, tighter_when_higher=False)
    if key == "constraints" and isinstance(before, dict) and isinstance(after, dict):
        return _classify_constraint_mapping(
            kind,
            path,
            cast(dict[str, object], before),
            cast(dict[str, object], after),
        )
    if key == "value" and kind == "python-api":
        return "review-required", "exported literal compatibility is not provable"
    return "review-required", "constraint compatibility is not provable"


def _classify_order(_before: object | None, _after: object | None) -> ClassificationResult:
    return "breaking", "positional member order changed"


def _classify_additional_properties(
    before: object | None,
    after: object | None,
) -> ClassificationResult:
    if before in {None, True} and after is False:
        return "breaking", "additional properties are no longer accepted"
    if before is False and after is True:
        return "compatible", "additional properties are now accepted"
    return "review-required", "additional-property compatibility is not provable"


def _classify_exclusive(
    before: object | None,
    after: object | None,
) -> ClassificationResult:
    if before is False and after is True:
        return "breaking", "constraint became exclusive"
    if before is True and after is False:
        return "compatible", "exclusive constraint was relaxed"
    return "review-required", "constraint exclusivity is not provable"


def _classify_incompatible_constraint(
    _before: object | None,
    _after: object | None,
) -> ClassificationResult:
    return "breaking", "accepted values changed incompatibly"


def _classify_enum(
    before: object | None,
    after: object | None,
) -> tuple[Classification, str]:
    old = _json_set(before)
    new = _json_set(after)
    if old < new:
        return "review-required", "enum expanded for potentially exhaustive consumers"
    if new < old:
        return "breaking", "accepted enum values were removed"
    return "review-required", "enum values changed incompatibly"


def _classify_bound(
    before: object | None,
    after: object | None,
    *,
    tighter_when_higher: bool,
) -> tuple[Classification, str]:
    if isinstance(before, (int, float)) and isinstance(after, (int, float)):
        tightened = after > before if tighter_when_higher else after < before
        if tightened:
            return "breaking", "accepted range narrowed"
        return "compatible", "accepted range widened"
    if before is None and after is not None:
        return "breaking", "new range constraint narrows accepted values"
    if before is not None and after is None:
        return "compatible", "range constraint was removed"
    return "review-required", "range compatibility is not provable"


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
    if "breaking" in results:
        return "breaking", "one or more accepted-value constraints tightened"
    if "review-required" in results:
        return "review-required", "one or more constraint changes require review"
    return "compatible", "accepted-value constraints were relaxed"


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


def _classify_contract_add(
    _kind: ContractKind,
    _path: str,
    _before: object | None,
    _after: object | None,
) -> ClassificationResult:
    return "compatible", "new contract surface"


def _classify_removal(
    _kind: ContractKind,
    _path: str,
    _before: object | None,
    _after: object | None,
) -> ClassificationResult:
    return "breaking", "contract surface removed"


def _classify_member_add_operation(
    kind: ContractKind,
    path: str,
    _before: object | None,
    after: object | None,
) -> ClassificationResult:
    return _classify_member_add(kind, path, after)


def _classify_rename_operation(
    _kind: ContractKind,
    _path: str,
    before: object | None,
    after: object | None,
) -> ClassificationResult:
    return _classify_rename(before, after)


def _classify_type_operation(
    _kind: ContractKind,
    path: str,
    before: object | None,
    after: object | None,
) -> ClassificationResult:
    return _classify_type(path, before, after)


def _classify_requiredness_operation(
    _kind: ContractKind,
    _path: str,
    before: object | None,
    after: object | None,
) -> ClassificationResult:
    return _classify_requiredness(before, after)


def _classify_default_operation(
    kind: ContractKind,
    path: str,
    before: object | None,
    after: object | None,
) -> ClassificationResult:
    return _classify_default(kind, path, before, after)


def _classify_alias_operation(
    _kind: ContractKind,
    _path: str,
    before: object | None,
    after: object | None,
) -> ClassificationResult:
    return _classify_aliases(before, after)


def _classify_unsupported_operation(
    _kind: ContractKind,
    _path: str,
    _before: object | None,
    _after: object | None,
) -> ClassificationResult:
    return "review-required", "unsupported semantics changed"


def _classify_constraint_operation(
    kind: ContractKind,
    path: str,
    before: object | None,
    after: object | None,
) -> ClassificationResult:
    return _classify_constraint(kind, path, before, after)


def _classify_unknown(
    _kind: ContractKind,
    _path: str,
    _before: object | None,
    _after: object | None,
) -> ClassificationResult:
    return "review-required", "unrecognized semantic operation"


type MemberAddClassifier = Callable[[str, Mapping[str, object]], ClassificationResult]
type ConstraintClassifier = Callable[[object | None, object | None], ClassificationResult]

MEMBER_ADD_CLASSIFIERS: dict[ContractKind, MemberAddClassifier] = {
    "cli-manifest": _classify_cli_member_add,
    "config-capabilities": _classify_config_member_add,
    "json-schema": _classify_schema_member_add,
    "python-api": _classify_python_member_add,
}
CONSTRAINT_CLASSIFIERS: dict[str, ConstraintClassifier] = {
    "additional_properties": _classify_additional_properties,
    "choices": _classify_enum,
    "const": _classify_incompatible_constraint,
    "enum": _classify_enum,
    "maximum_exclusive": _classify_exclusive,
    "minimum_exclusive": _classify_exclusive,
    "order": _classify_order,
    "pattern": _classify_incompatible_constraint,
}
OPERATION_CLASSIFIERS: dict[str, Classifier] = {
    "alias-change": _classify_alias_operation,
    "constraint-change": _classify_constraint_operation,
    "contract-add": _classify_contract_add,
    "contract-remove": _classify_removal,
    "default-change": _classify_default_operation,
    "member-add": _classify_member_add_operation,
    "member-remove": _classify_removal,
    "member-rename": _classify_rename_operation,
    "requiredness-change": _classify_requiredness_operation,
    "type-change": _classify_type_operation,
    "unsupported-semantic-change": _classify_unsupported_operation,
}
