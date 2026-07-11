"""Resolved configuration value type checks."""

from __future__ import annotations

from collections.abc import Callable

from agent_maintainer.config import registry


def type_message(value: object, spec: registry.ConfigFieldSpec) -> str:
    """Return a stable type error message, or an empty string when valid."""

    handlers: dict[str, Callable[[object, registry.ConfigFieldSpec], str]] = {
        "bool": _bool_message,
        "int": _int_message,
        "non-negative-int": _int_message,
        "float": _float_message,
        "str": _str_message,
        "choice": _str_message,
        "tuple": _tuple_message,
    }
    handler = handlers.get(spec.value_kind)
    return "" if handler is None else handler(value, spec)


def _bool_message(value: object, _spec: registry.ConfigFieldSpec) -> str:
    return "" if isinstance(value, bool) else "must be a boolean"


def _int_message(value: object, _spec: registry.ConfigFieldSpec) -> str:
    valid = isinstance(value, int) and not isinstance(value, bool)
    return "" if valid else "must be an integer (booleans are not integers)"


def _float_message(value: object, _spec: registry.ConfigFieldSpec) -> str:
    valid = isinstance(value, (float, int)) and not isinstance(value, bool)
    return "" if valid else "must be a finite number"


def _str_message(value: object, spec: registry.ConfigFieldSpec) -> str:
    valid = isinstance(value, str) and (spec.allow_empty or bool(value.strip()))
    return "" if valid else "must be a non-empty string"


def _tuple_message(value: object, _spec: registry.ConfigFieldSpec) -> str:
    valid = isinstance(value, tuple) and all(isinstance(item, str) for item in value)
    return "" if valid else "must be a list of strings"
