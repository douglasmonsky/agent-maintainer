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


def _string_tuple(value: object, field_name: str) -> tuple[str, ...]:
    values = json_array(value)
    if values is None:
        raise TypeError(f"{field_name} must be a list of strings")
    strings = tuple(item for item in values if isinstance(item, str))
    if len(strings) != len(values):
        raise TypeError(f"{field_name} must be a list of strings")
    return strings


def coerce_cpp(raw_value: object, *, source: str = "configuration") -> CppCmakeConfig:
    """Coerce the provider-owned C/C++ table without shell shortcuts."""

    raw = json_object(raw_value)
    if raw is None:
        raise TypeError("cpp must be a table")
    validation.validate_raw_config({"cpp": raw}, source=source)
    updates: dict[str, object] = {
        name: _string_tuple(raw[name], f"cpp.{name}") for name in CPP_TUPLE_FIELDS if name in raw
    }
    if "enabled" in raw:
        enabled = raw["enabled"]
        if not isinstance(enabled, bool):
            raise TypeError("cpp.enabled must be a boolean")
        updates["enabled"] = enabled
    if "cmake_root" in raw:
        cmake_root = raw["cmake_root"]
        if not isinstance(cmake_root, str) or not cmake_root:
            raise TypeError("cpp.cmake_root must be a non-empty string")
        updates["cmake_root"] = cmake_root
    return replace(CppCmakeConfig(), **updates)
