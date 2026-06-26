"""Coercion helpers for guardrail configuration values."""

from __future__ import annotations

from typing import Any

from guardrail_lib.config import schema


def as_tuple(value: object, field_name: str) -> tuple[str, ...]:
    """Coerce a string or list-like value into a tuple of normalized paths."""

    if value is None:
        return ()
    if isinstance(value, str):
        items = [part.strip() for part in value.split(",")]
    elif isinstance(value, (list, tuple)):
        items = [str(part).strip() for part in value]
    else:
        raise TypeError(f"{field_name} must be a string or list of strings")
    return tuple(item.rstrip("/") or "." for item in items if item)


def as_bool(value: object, field_name: str) -> bool:
    """Coerce a bool-like config value."""

    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise TypeError(f"{field_name} must be a boolean")


def as_int(value: object, field_name: str) -> int:
    """Coerce an integer config value."""

    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be an integer")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{field_name} must be an integer") from exc


def as_str(value: object, field_name: str) -> str:
    """Coerce a non-empty string config value."""

    if isinstance(value, str) and value:
        return value
    raise TypeError(f"{field_name} must be a non-empty string")


def as_choice(value: object, field_name: str, choices: frozenset[str]) -> str:
    """Coerce a string config value constrained to an allowed choice set."""

    selected = as_str(value, field_name)
    if selected in choices:
        return selected
    valid_values = ", ".join(sorted(choices))
    raise TypeError(f"{field_name} must be one of: {valid_values}")


DIAGNOSTIC_FIELD_PARSERS = (
    ("enabled", "diagnostic_artifacts_enabled", as_bool),
    ("log_dir", "diagnostic_artifacts_dir", as_str),
)


def coerce_diagnostics(raw_value: object) -> dict[str, object]:
    """Coerce the nested diagnostics config table."""

    if not isinstance(raw_value, dict):
        raise TypeError("diagnostics must be a table")
    updates: dict[str, object] = {}
    for raw_name, field_name, parser in DIAGNOSTIC_FIELD_PARSERS:
        value = raw_value.get(raw_name)
        if value is not None:
            updates[field_name] = parser(value, f"diagnostics.{raw_name}")
    return updates


def coerce_updates(raw: dict[str, Any]) -> dict[str, object]:
    """Coerce raw pyproject config values into dataclass update values."""

    updates: dict[str, object] = {}
    field_parsers = (
        (schema.TUPLE_FIELDS, as_tuple),
        (schema.BOOL_FIELDS, as_bool),
        (schema.INT_FIELDS, as_int),
        (schema.STR_FIELDS, as_str),
    )
    for fields, parser in field_parsers:
        for field_name in fields:
            raw_value = raw.get(field_name)
            if raw_value is not None:
                updates[field_name] = parser(raw_value, field_name)
    architecture_tool = raw.get("architecture_tool")
    if architecture_tool is not None:
        updates["architecture_tool"] = as_choice(
            architecture_tool, "architecture_tool", schema.VALID_ARCHITECTURE_TOOLS
        )
    diagnostics = raw.get("diagnostics")
    if diagnostics is not None:
        updates.update(coerce_diagnostics(diagnostics))
    return updates
