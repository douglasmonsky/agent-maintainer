"""Bounded structural JSON Schema contract extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import cast

from agent_maintainer.contracts.baseline import canonical_json
from agent_maintainer.contracts.limits import MAX_DEPTH, MAX_MEMBERS
from agent_maintainer.contracts.models import ContractSpec, Descriptor, ExtractionError
from agent_maintainer.contracts.normalization import (
    build_descriptor,
    exact_keys,
    load_json_object,
    safe_text,
    text_array,
    validate_json_value,
)
from agent_maintainer.contracts.validation import require

SCHEMA_KEYS = frozenset(
    (
        "$defs",
        "$id",
        "$ref",
        "$schema",
        "additionalProperties",
        "allOf",
        "anyOf",
        "const",
        "description",
        "else",
        "enum",
        "exclusiveMaximum",
        "exclusiveMinimum",
        "if",
        "items",
        "maxItems",
        "maxLength",
        "maximum",
        "minItems",
        "minLength",
        "minimum",
        "not",
        "oneOf",
        "pattern",
        "properties",
        "required",
        "then",
        "title",
        "type",
    )
)
COMPOSITION_KEYS = (
    "allOf",
    "anyOf",
    "else",
    "if",
    "not",
    "oneOf",
    "then",
)
ALLOWED_TYPES = frozenset(("array", "boolean", "integer", "null", "number", "object", "string"))
NONNEGATIVE_KEYS = MappingProxyType(
    {
        "maxItems": "max_items",
        "maxLength": "max_length",
        "minItems": "min_items",
        "minLength": "min_length",
    }
)
NUMERIC_KEYS = MappingProxyType(
    {
        "exclusiveMaximum": "exclusive_maximum",
        "exclusiveMinimum": "exclusive_minimum",
        "maximum": "maximum",
        "minimum": "minimum",
    }
)


@dataclass
class _Context:
    definitions: dict[str, dict[str, object]]
    unsupported: set[str]


@dataclass(frozen=True)
class _Visit:
    context: _Context
    path: str
    depth: int
    stack: tuple[str, ...]


def extract_json_schema(repo_root: Path, spec: ContractSpec) -> Descriptor:
    """Extract the supported structural subset of one confined JSON Schema."""

    if spec.kind != "json-schema":
        raise ExtractionError("JSON Schema extractor requires json-schema kind")
    document = load_json_object(repo_root, spec)
    context = _Context(definitions=_definitions(document), unsupported=set())
    body = _normalize_schema(document, context=context, path="", depth=0, stack=())
    body["unsupported_semantics"] = sorted(context.unsupported)
    return build_descriptor(spec, body)


def _definitions(document: dict[str, object]) -> dict[str, dict[str, object]]:
    value = document.get("$defs", {})
    if not isinstance(value, dict):
        raise ExtractionError("$defs must be an object")
    raw = cast(dict[str, object], value)
    if len(raw) > MAX_MEMBERS:
        raise ExtractionError("$defs must be bounded")
    definitions: dict[str, dict[str, object]] = {}
    for name, schema in raw.items():
        safe_text(name, label="JSON definition name")
        if not isinstance(schema, dict):
            raise ExtractionError("JSON definition must be an object")
        definitions[name] = cast(dict[str, object], schema)
    return definitions


def _normalize_schema(
    schema: dict[str, object],
    *,
    context: _Context,
    path: str,
    depth: int,
    stack: tuple[str, ...],
) -> dict[str, object]:
    if depth > MAX_DEPTH:
        raise ExtractionError("JSON Schema exceeds maximum depth")
    exact_keys(schema, SCHEMA_KEYS, label="schema", required=frozenset())
    reference = schema.get("$ref")
    if reference is None:
        normalized = {}
    else:
        normalized = _resolve_ref(
            reference,
            context=context,
            path=path,
            depth=depth,
            stack=stack,
        )
    _normalize_annotations(schema, normalized)
    _normalize_types(schema, normalized)
    visit = _Visit(context=context, path=path, depth=depth, stack=stack)
    _normalize_properties(schema, normalized, visit)
    _normalize_additional_properties(schema, normalized, visit)
    _normalize_items(schema, normalized, visit)
    _normalize_constraints(schema, normalized)
    _record_unsupported(schema, context=context, path=path)
    return normalized


def _resolve_ref(
    value: object,
    *,
    context: _Context,
    path: str,
    depth: int,
    stack: tuple[str, ...],
) -> dict[str, object]:
    reference = safe_text(value, label="JSON reference")
    prefix = "#/$defs/"
    require(reference.startswith(prefix), "unsupported or unsafe JSON reference", ExtractionError)
    encoded_name = reference.removeprefix(prefix)
    require(
        bool(encoded_name) and re.search(r"~(?![01])", encoded_name) is None,
        "unsupported or unsafe JSON reference",
        ExtractionError,
    )
    name = encoded_name.replace("~1", "/").replace("~0", "~")
    require(name not in stack, "JSON reference cycle", ExtractionError)
    definition = context.definitions.get(name)
    require(definition is not None, f"missing JSON definition: {name}", ExtractionError)
    return _normalize_schema(
        cast(dict[str, object], definition),
        context=context,
        path=path,
        depth=depth + 1,
        stack=(*stack, name),
    )


def _normalize_annotations(schema: dict[str, object], output: dict[str, object]) -> None:
    identifier = schema.get("$id")
    if identifier is not None:
        output["id"] = safe_text(identifier, label="schema id")
    for key in ("$schema", "description", "title"):
        value = schema.get(key)
        if value is not None:
            safe_text(value, label=f"schema {key}")


def _normalize_types(schema: dict[str, object], output: dict[str, object]) -> None:
    value = schema.get("type")
    if value is None:
        return
    if isinstance(value, str):
        types = [safe_text(value, label="schema type")]
    else:
        types = text_array(value, label="schema type", allow_empty=False)
    if any(item not in ALLOWED_TYPES for item in types):
        raise ExtractionError("unsupported schema type")
    output["types"] = sorted(types)


def _normalize_properties(
    schema: dict[str, object],
    output: dict[str, object],
    visit: _Visit,
) -> None:
    properties, required = _schema_properties(schema)
    if properties is None:
        return
    normalized: dict[str, object] = {}
    for name in sorted(properties):
        safe_text(name, label="property name")
        child = properties[name]
        if not isinstance(child, dict):
            raise ExtractionError("property schema must be an object")
        member = _normalize_schema(
            cast(dict[str, object], child),
            context=visit.context,
            path=_pointer(visit.path, "properties", name),
            depth=visit.depth + 1,
            stack=visit.stack,
        )
        member["required"] = name in required
        normalized[name] = member
    output["properties"] = normalized


def _schema_properties(
    schema: dict[str, object],
) -> tuple[dict[str, object] | None, list[str]]:
    value = schema.get("properties")
    required = text_array(schema.get("required", []), label="required property")
    if value is None:
        require(not required, "required property is missing from properties", ExtractionError)
        return None, required
    require(isinstance(value, dict), "properties must be an object", ExtractionError)
    properties = cast(dict[str, object], value)
    require(len(properties) <= MAX_MEMBERS, "properties must be bounded", ExtractionError)
    missing = sorted(set(required) - set(properties))
    missing_name = missing[0] if missing else ""
    require(not missing, f"required property is missing: {missing_name}", ExtractionError)
    return properties, required


def _normalize_additional_properties(
    schema: dict[str, object],
    output: dict[str, object],
    visit: _Visit,
) -> None:
    additional = schema.get("additionalProperties")
    if additional is not None:
        output["additional_properties"] = _additional_properties(
            additional,
            visit=_Visit(
                context=visit.context,
                path=_pointer(visit.path, "additionalProperties"),
                depth=visit.depth,
                stack=visit.stack,
            ),
        )


def _additional_properties(
    value: object,
    *,
    visit: _Visit,
) -> object:
    if isinstance(value, bool):
        return value
    if isinstance(value, dict):
        return _normalize_schema(
            cast(dict[str, object], value),
            context=visit.context,
            path=visit.path,
            depth=visit.depth + 1,
            stack=visit.stack,
        )
    raise ExtractionError("additionalProperties must be boolean or an object")


def _normalize_items(
    schema: dict[str, object],
    output: dict[str, object],
    visit: _Visit,
) -> None:
    value = schema.get("items")
    if value is None:
        return
    if not isinstance(value, dict):
        raise ExtractionError("items must be an object")
    output["items"] = _normalize_schema(
        cast(dict[str, object], value),
        context=visit.context,
        path=_pointer(visit.path, "items"),
        depth=visit.depth + 1,
        stack=visit.stack,
    )


def _normalize_constraints(schema: dict[str, object], output: dict[str, object]) -> None:
    for source, target in NUMERIC_KEYS.items():
        if source in schema:
            output[target] = _number(schema.get(source), label=source)
    for source, target in NONNEGATIVE_KEYS.items():
        if source in schema:
            output[target] = _nonnegative_integer(schema.get(source), label=source)
    _normalize_pattern(schema, output)
    if "enum" in schema:
        output["enum"] = _sorted_unique_json(schema.get("enum"), label="schema enum")
    if "const" in schema:
        constant = schema.get("const")
        validate_json_value(constant)
        output["const"] = constant


def _normalize_pattern(schema: dict[str, object], output: dict[str, object]) -> None:
    if "pattern" not in schema:
        return
    pattern = safe_text(schema["pattern"], label="schema pattern")
    try:
        re.compile(pattern)
    except re.error as exc:
        raise ExtractionError("schema pattern must be a valid regular expression") from exc
    output["pattern"] = pattern


def _number(value: object, *, label: str) -> int | float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ExtractionError(f"{label} must be numeric")
    validate_json_value(value)
    return value


def _nonnegative_integer(value: object, *, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ExtractionError(f"{label} must be a non-negative integer")
    return value


def _sorted_unique_json(value: object, *, label: str) -> list[object]:
    if not isinstance(value, list):
        raise ExtractionError(f"{label} must be a bounded array")
    values = cast(list[object], value)
    if len(values) > MAX_MEMBERS:
        raise ExtractionError(f"{label} must be a bounded array")
    keyed: dict[str, object] = {}
    for item in values:
        validate_json_value(item)
        encoded = canonical_json(item)
        if encoded in keyed:
            raise ExtractionError(f"duplicate {label}")
        keyed[encoded] = item
    return [keyed[key] for key in sorted(keyed)]


def _record_unsupported(schema: dict[str, object], *, context: _Context, path: str) -> None:
    for keyword in COMPOSITION_KEYS:
        if keyword in schema:
            context.unsupported.add(_pointer(path, keyword))


def _pointer(path: str, *parts: str) -> str:
    encoded = [part.replace("~", "~0").replace("/", "~1") for part in parts]
    suffix = "/".join(encoded)
    return f"{path}/{suffix}"
