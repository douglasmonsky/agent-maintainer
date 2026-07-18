"""Shared bounded JSON normalization for semantic contract extractors."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from agent_maintainer.contracts.baseline import canonical_json, fingerprint
from agent_maintainer.contracts.limits import MAX_DEPTH, MAX_MEMBERS
from agent_maintainer.contracts.models import ContractSpec, Descriptor, ExtractionError
from agent_maintainer.contracts.paths import read_confined_text

FIRST_SAFE_CODEPOINT = ord(" ")


def build_descriptor(spec: ContractSpec, body: dict[str, object]) -> Descriptor:
    """Build one fingerprinted descriptor from normalized semantic facts."""

    semantic = {
        "body": body,
        "contract_id": spec.id,
        "kind": spec.kind,
        "owner": spec.owner,
        "revision": spec.revision,
        "sources": [spec.source],
        "stability": spec.stability,
    }
    return Descriptor(
        contract_id=spec.id,
        kind=spec.kind,
        owner=spec.owner,
        stability=spec.stability,
        revision=spec.revision,
        sources=(spec.source,),
        body=body,
        fingerprint=fingerprint(semantic),
    )


def load_json_object(repo_root: Path, spec: ContractSpec) -> dict[str, object]:
    """Load one bounded duplicate-free JSON object from the configured source."""

    text = read_confined_text(repo_root, spec.source, label=f"contract {spec.id}")
    try:
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise ExtractionError("source must contain valid JSON") from exc
    if not isinstance(value, dict):
        raise ExtractionError("source must contain a JSON object")
    document = cast(dict[str, object], value)
    validate_json_value(document)
    return document


def exact_keys(
    raw: Mapping[str, object],
    allowed: frozenset[str],
    *,
    label: str,
    required: frozenset[str] | None = None,
) -> None:
    """Reject unknown and required-missing keys with bounded messages."""

    unknown = sorted(set(raw) - allowed)
    required_keys = allowed if required is None else required
    missing = sorted(required_keys - set(raw))
    if unknown:
        raise ExtractionError(f"unknown {label} key: {unknown[0]}")
    if missing:
        raise ExtractionError(f"{label} missing key: {missing[0]}")


def object_array(value: object, *, label: str) -> list[dict[str, object]]:
    """Return a bounded array of JSON objects."""

    if not isinstance(value, list):
        raise ExtractionError(f"{label} must be a bounded array")
    values = cast(list[object], value)
    if len(values) > MAX_MEMBERS:
        raise ExtractionError(f"{label} must be a bounded array")
    if not all(isinstance(item, dict) for item in values):
        raise ExtractionError(f"{label} must contain objects")
    return [cast(dict[str, object], item) for item in values]


def safe_text(value: object, *, label: str) -> str:
    """Return nonempty control-free text."""

    if (
        not isinstance(value, str)
        or not value
        or any(ord(character) < FIRST_SAFE_CODEPOINT for character in value)
    ):
        raise ExtractionError(f"{label} must be non-empty safe text")
    return value


def text_array(
    value: object,
    *,
    label: str,
    allow_empty: bool = True,
) -> list[str]:
    """Return bounded unique control-free text in authored order."""

    if not isinstance(value, list):
        raise ExtractionError(f"{label} must be an array of safe text")
    values = cast(list[object], value)
    if len(values) > MAX_MEMBERS or (not allow_empty and not values):
        raise ExtractionError(f"{label} must be a bounded non-empty array")
    result = [safe_text(item, label=label) for item in values]
    if len(result) != len(set(result)):
        raise ExtractionError(f"duplicate {label}")
    return result


def sorted_json_scalars(value: object, *, label: str) -> list[object]:
    """Return a stable unique array of JSON scalar choices."""

    if not isinstance(value, list):
        raise ExtractionError(f"{label} must be an array")
    values = cast(list[object], value)
    if len(values) > MAX_MEMBERS:
        raise ExtractionError(f"{label} must be a bounded array")
    if not all(item is None or isinstance(item, (bool, int, float, str)) for item in values):
        raise ExtractionError(f"{label} must contain JSON scalars")
    for item in values:
        validate_json_value(item)
    keyed = {canonical_json(item): item for item in values}
    if len(keyed) != len(values):
        raise ExtractionError(f"duplicate {label}")
    return [keyed[key] for key in sorted(keyed)]


def validate_json_value(value: object, *, depth: int = 0) -> None:
    """Reject noncanonical, excessive, or non-finite JSON-compatible values."""

    if depth > MAX_DEPTH:
        raise ExtractionError("JSON value exceeds maximum depth")
    if value is None or isinstance(value, (bool, int, str)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ExtractionError("JSON numbers must be finite")
        return
    if isinstance(value, list):
        _validate_array(cast(list[object], value), depth=depth)
        return
    if isinstance(value, dict):
        _validate_object(cast(dict[object, object], value), depth=depth)
        return
    raise ExtractionError("value must be canonical JSON")


def _validate_array(values: list[object], *, depth: int) -> None:
    if len(values) > MAX_MEMBERS:
        raise ExtractionError("JSON array must be bounded")
    for item in values:
        validate_json_value(item, depth=depth + 1)


def _validate_object(mapping: dict[object, object], *, depth: int) -> None:
    if len(mapping) > MAX_MEMBERS or not all(isinstance(key, str) for key in mapping):
        raise ExtractionError("JSON object must be bounded with text keys")
    for key, item in mapping.items():
        safe_text(key, label="JSON object key")
        validate_json_value(item, depth=depth + 1)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ExtractionError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> object:
    raise ExtractionError(f"JSON numbers must be finite: {value}")
