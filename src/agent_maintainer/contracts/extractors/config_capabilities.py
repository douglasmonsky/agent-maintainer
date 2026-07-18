"""Strict configuration-capability manifest extraction."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from agent_maintainer.contracts.limits import MAX_MEMBERS
from agent_maintainer.contracts.models import ContractSpec, Descriptor, ExtractionError
from agent_maintainer.contracts.normalization import (
    build_descriptor,
    exact_keys,
    load_json_object,
    object_array,
    safe_text,
    sorted_json_scalars,
    text_array,
    validate_json_value,
)

DOCUMENT_KEYS = frozenset(
    (
        "fields",
        "nested_environment",
        "nested_tables",
        "precedence",
        "runtime_environment",
        "schema_version",
    )
)
FIELD_KEYS = frozenset(
    (
        "cli_override",
        "constraints",
        "default",
        "description",
        "environment",
        "environment_style",
        "label",
        "name",
        "stability",
        "toml_aliases",
        "toml_key",
        "value_kind",
    )
)
CONSTRAINT_KEYS = frozenset(
    (
        "allow_empty",
        "choices",
        "maximum",
        "minimum",
        "minimum_exclusive",
        "repository_relative_path",
        "verification_profiles",
    )
)
STABILITIES = frozenset(("beta", "stable"))


def extract_config_capabilities(repo_root: Path, spec: ContractSpec) -> Descriptor:
    """Extract normalized configuration fields from one strict manifest."""

    document = load_json_object(repo_root, spec)
    _validate_document(spec, document)
    return build_descriptor(spec, {"fields": _normalized_fields(document)})


def _validate_document(spec: ContractSpec, document: dict[str, object]) -> None:
    if spec.kind != "config-capabilities":
        raise ExtractionError("config extractor requires config-capabilities kind")
    exact_keys(document, DOCUMENT_KEYS, label="manifest")
    if document.get("schema_version") != 1 or isinstance(document.get("schema_version"), bool):
        raise ExtractionError("manifest schema_version must be exactly 1")
    _validate_supporting_tables(document)


def _normalized_fields(document: dict[str, object]) -> list[dict[str, object]]:
    fields = object_array(document.get("fields"), label="fields")
    if len(fields) > MAX_MEMBERS:
        raise ExtractionError("fields must be a bounded array")
    normalized = [_normalize_field(field) for field in fields]
    identities = [field["name"] for field in normalized]
    if len(identities) != len(set(identities)):
        raise ExtractionError("duplicate field identity")
    normalized.sort(key=lambda item: str(item["name"]))
    return normalized


def _validate_supporting_tables(document: dict[str, object]) -> None:
    for key in ("nested_environment", "nested_tables"):
        table = document.get(key)
        if not isinstance(table, dict):
            raise ExtractionError(f"{key} must be an object")
        validate_json_value(cast(dict[str, object], table))
    text_array(document.get("precedence"), label="precedence")
    text_array(document.get("runtime_environment"), label="runtime environment")


def _normalize_field(raw: dict[str, object]) -> dict[str, object]:
    exact_keys(raw, FIELD_KEYS, label="field")
    name = safe_text(raw.get("name"), label="field name")
    for key in ("cli_override", "description", "label", "toml_key"):
        safe_text(raw.get(key), label=f"field {key}")
    environment_style = raw.get("environment_style")
    if environment_style is not None:
        safe_text(environment_style, label="field environment_style")
    stability = safe_text(raw.get("stability"), label="field stability")
    if stability not in STABILITIES:
        raise ExtractionError("field stability must be beta or stable")
    default = raw.get("default")
    validate_json_value(default)
    constraints, choices = _normalize_constraints(raw.get("constraints"))
    aliases = sorted(text_array(raw.get("toml_aliases"), label="field alias"))
    environment_value = raw.get("environment")
    environment = (
        []
        if environment_value is None
        else [safe_text(environment_value, label="field environment")]
    )
    return {
        "aliases": aliases,
        "choices": choices,
        "constraints": constraints,
        "default": default,
        "environment": environment,
        "kind": safe_text(raw.get("value_kind"), label="field kind"),
        "name": name,
        "required": False,
        "stability": stability,
    }


def _normalize_constraints(value: object) -> tuple[dict[str, object], list[object]]:
    if not isinstance(value, dict):
        raise ExtractionError("field constraints must be an object")
    constraints = dict(cast(dict[str, object], value))
    exact_keys(constraints, CONSTRAINT_KEYS, label="constraint")
    for key in (
        "allow_empty",
        "minimum_exclusive",
        "repository_relative_path",
        "verification_profiles",
    ):
        if not isinstance(constraints.get(key), bool):
            raise ExtractionError(f"constraint {key} must be boolean")
    for key in ("minimum", "maximum"):
        number = constraints.get(key)
        if number is not None and (
            not isinstance(number, (int, float)) or isinstance(number, bool)
        ):
            raise ExtractionError(f"constraint {key} must be numeric or null")
        validate_json_value(number)
    choices = sorted_json_scalars(constraints.pop("choices"), label="field choices")
    return constraints, choices
