"""Small shared guard for explicit contract validation failures."""

from __future__ import annotations

import math
from typing import cast

from agent_maintainer.contracts.limits import MAX_DEPTH, MAX_MEMBERS

FIRST_SAFE_CODEPOINT = ord(" ")


def require(condition: bool, message: str, error_type: type[Exception]) -> None:
    """Raise the nominated validation error when a condition is false."""

    if not condition:
        raise error_type(message)


def validate_json_value(
    value: object,
    *,
    error_type: type[Exception],
    depth: int = 0,
) -> None:
    """Reject excessive, non-finite, or noncanonical JSON-compatible values."""

    require(depth <= MAX_DEPTH, "JSON value exceeds maximum depth", error_type)
    if _is_scalar(value):
        return
    if isinstance(value, float):
        _validate_number(value, error_type)
        return
    if isinstance(value, list):
        _validate_array(cast(list[object], value), error_type=error_type, depth=depth)
        return
    if isinstance(value, dict):
        _validate_object(cast(dict[object, object], value), error_type=error_type, depth=depth)
        return
    raise error_type("value must be canonical JSON")


def _is_scalar(value: object) -> bool:
    return value is None or isinstance(value, (bool, int, str))


def _validate_number(value: float, error_type: type[Exception]) -> None:
    require(math.isfinite(value), "JSON numbers must be finite", error_type)


def _validate_array(
    values: list[object],
    *,
    error_type: type[Exception],
    depth: int,
) -> None:
    require(len(values) <= MAX_MEMBERS, "JSON array must be bounded", error_type)
    for item in values:
        validate_json_value(item, error_type=error_type, depth=depth + 1)


def _validate_object(
    mapping: dict[object, object],
    *,
    error_type: type[Exception],
    depth: int,
) -> None:
    valid = len(mapping) <= MAX_MEMBERS and all(_safe_key(key) for key in mapping)
    require(valid, "JSON object must be bounded with safe text keys", error_type)
    for item in mapping.values():
        validate_json_value(item, error_type=error_type, depth=depth + 1)


def _safe_key(value: object) -> bool:
    return bool(
        isinstance(value, str)
        and value
        and all(ord(character) >= FIRST_SAFE_CODEPOINT for character in value)
    )
