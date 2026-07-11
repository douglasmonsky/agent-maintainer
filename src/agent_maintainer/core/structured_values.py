"""Typed normalization helpers for decoded structured artifacts."""

from __future__ import annotations

from typing import cast


def json_object(value: object) -> dict[str, object] | None:
    """Return a JSON object with string keys, or ``None`` when malformed."""

    if not isinstance(value, dict):
        return None
    raw = cast(dict[object, object], value)
    if not all(isinstance(key, str) for key in raw):
        return None
    return {key: item for key, item in raw.items() if isinstance(key, str)}


def json_array(value: object) -> list[object] | None:
    """Return a JSON array with an explicit element boundary."""

    if not isinstance(value, list):
        return None
    return cast(list[object], value)


def json_object_items(value: object) -> list[tuple[str, object]]:
    """Return valid string-keyed fields while isolating malformed neighbors."""

    if not isinstance(value, dict):
        return []
    raw = cast(dict[object, object], value)
    return [(key, item) for key, item in raw.items() if isinstance(key, str)]


def json_objects(values: list[object]) -> list[dict[str, object]]:
    """Return the valid string-keyed objects from one JSON array."""

    objects: list[dict[str, object]] = []
    for value in values:
        item = json_object(value)
        if item is not None:
            objects.append(item)
    return objects


def plain_int(value: object, *, default: int = 0) -> int:
    """Return a non-boolean integer, or a safe fallback."""

    return value if isinstance(value, int) and not isinstance(value, bool) else default
