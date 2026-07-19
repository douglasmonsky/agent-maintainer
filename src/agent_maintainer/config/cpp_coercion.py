"""Coercion for nested C/C++ CMake provider configuration."""

from __future__ import annotations

from dataclasses import replace

from agent_maintainer.config import validation
from agent_maintainer.config.cpp import CppCmakeConfig
from agent_maintainer.core.structured_values import json_array, json_object

CPP_TUPLE_FIELDS = (
    "format_command",
    "static_analysis_command",
    "build_command",
    "test_command",
    "coverage_command",
    "format_profiles",
    "static_analysis_profiles",
    "build_profiles",
    "test_profiles",
    "coverage_profiles",
)
_MISSING = object()


def _string_tuple(value: object, field_name: str) -> tuple[str, ...]:
    values = json_array(value)
    if values is None:
        raise TypeError(f"{field_name} must be a list of strings")
    strings = tuple(item for item in values if isinstance(item, str))
    if len(strings) != len(values):
        raise TypeError(f"{field_name} must be a list of strings")
    return strings


def _cpp_table(raw_value: object, *, source: str) -> dict[str, object]:
    raw = json_object(raw_value)
    if raw is None:
        raise TypeError("cpp must be a table")
    validation.validate_raw_config({"cpp": raw}, source=source)
    return raw


def _tuple_updates(raw: dict[str, object]) -> dict[str, object]:
    return {
        name: _string_tuple(raw[name], f"cpp.{name}") for name in CPP_TUPLE_FIELDS if name in raw
    }


def _enabled_update(raw: dict[str, object]) -> dict[str, object]:
    enabled = raw.get("enabled", _MISSING)
    if enabled is _MISSING:
        return {}
    if not isinstance(enabled, bool):
        raise TypeError("cpp.enabled must be a boolean")
    return {"enabled": enabled}


def _cmake_root_update(raw: dict[str, object]) -> dict[str, object]:
    cmake_root = raw.get("cmake_root", _MISSING)
    if cmake_root is _MISSING:
        return {}
    if not isinstance(cmake_root, str) or not cmake_root:
        raise TypeError("cpp.cmake_root must be a non-empty string")
    return {"cmake_root": cmake_root}


def coerce_cpp(raw_value: object, *, source: str = "configuration") -> CppCmakeConfig:
    """Coerce the provider-owned C/C++ table without shell shortcuts."""

    raw = _cpp_table(raw_value, source=source)
    updates = _tuple_updates(raw)
    updates.update(_enabled_update(raw))
    updates.update(_cmake_root_update(raw))
    return replace(CppCmakeConfig(), **updates)


def coerce_cpp_update(raw: dict[str, object], *, source: str) -> dict[str, object]:
    """Coerce the nested C/C++ table when present in raw configuration."""
    cpp = raw.get("cpp")
    if cpp is None:
        return {}
    return {"cpp": coerce_cpp(cpp, source=source)}
