"""Typed normalization helpers for decoded run artifacts."""

from __future__ import annotations

from typing import cast


def json_object(value: object) -> dict[str, object] | None:
    """Return a decoded object only when every key is a string."""

    if not isinstance(value, dict):
        return None
    raw = cast(dict[object, object], value)
    if not all(isinstance(key, str) for key in raw):
        return None
    return {key: item for key, item in raw.items() if isinstance(key, str)}


def json_array(value: object) -> list[object] | None:
    """Return a decoded array with an explicit element boundary."""

    if not isinstance(value, list):
        return None
    return cast(list[object], value)


def json_objects(value: object) -> list[dict[str, object]]:
    """Return valid string-keyed objects from a decoded array."""

    values = json_array(value)
    if values is None:
        return []
    objects: list[dict[str, object]] = []
    for item in values:
        parsed = json_object(item)
        if parsed is not None:
            objects.append(parsed)
    return objects
