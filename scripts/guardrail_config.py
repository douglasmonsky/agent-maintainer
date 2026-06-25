#!/usr/bin/env python3
"""Shared configuration for the guardrail scripts.

Configuration precedence, lowest to highest:
1. Built-in defaults.
2. [tool.ai_guardrails] in pyproject.toml.
3. GUARDRAILS_* environment variables.
4. Script-specific CLI overrides.
"""

from __future__ import annotations

import os
import shlex
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback if tomli is installed.
    import tomli as tomllib  # type: ignore[no-redef]


DEFAULT_SOURCE_ROOTS = ("src",)
DEFAULT_TEST_ROOTS = ("tests",)
DEFAULT_PACKAGE_PATHS = ("src",)
DEFAULT_COVERAGE_SOURCE = ("src",)
DEFAULT_FILE_LENGTH_PATHS = ("src", "tests", "scripts", ".codex/hooks")
DEFAULT_VULTURE_PATHS = ("src", "tests", "scripts")


@dataclass(frozen=True)
class GuardrailConfig:
    source_roots: tuple[str, ...] = DEFAULT_SOURCE_ROOTS
    test_roots: tuple[str, ...] = DEFAULT_TEST_ROOTS
    package_paths: tuple[str, ...] = DEFAULT_PACKAGE_PATHS
    coverage_source: tuple[str, ...] = DEFAULT_COVERAGE_SOURCE
    file_length_paths: tuple[str, ...] = DEFAULT_FILE_LENGTH_PATHS
    vulture_paths: tuple[str, ...] = DEFAULT_VULTURE_PATHS
    require_tests: bool = True
    coverage_fail_under: int = 80
    diff_cover_fail_under: int = 90
    file_length_max_physical: int = 600
    file_length_max_source: int = 450
    change_warn_lines: int = 300
    change_block_lines: int = 800
    change_warn_files: int = 8
    change_block_files: int = 20
    suppression_max_new: int = 3
    xenon_max_absolute: str = "B"
    xenon_max_modules: str = "A"
    xenon_max_average: str = "A"
    ruff_max_complexity: int = 10
    pyright_type_checking_mode: str = "standard"
    enable_pip_audit: bool = False
    pip_audit_args: tuple[str, ...] = ()


def _as_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        items = [part.strip() for part in value.split(",")]
    elif isinstance(value, (list, tuple)):
        items = [str(part).strip() for part in value]
    else:
        raise TypeError(f"{field_name} must be a string or list of strings")
    return tuple(item.rstrip("/") or "." for item in items if item)


def _as_bool(value: object, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise TypeError(f"{field_name} must be a boolean")


def _as_int(value: object, field_name: str) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{field_name} must be an integer") from exc


def _as_str(value: object, field_name: str) -> str:
    if isinstance(value, str) and value:
        return value
    raise TypeError(f"{field_name} must be a non-empty string")


def _read_pyproject(path: Path | None = None) -> dict[str, Any]:
    path = path or Path("pyproject.toml")
    if not path.exists():
        return {}
    with path.open("rb") as handle:
        payload = tomllib.load(handle)
    tool = payload.get("tool", {})
    if not isinstance(tool, dict):
        return {}
    config = tool.get("ai_guardrails", {})
    if not isinstance(config, dict):
        return {}
    return config


def _apply_pyproject(config: GuardrailConfig, raw: dict[str, Any]) -> GuardrailConfig:
    updates: dict[str, object] = {}
    tuple_fields = {
        "source_roots",
        "test_roots",
        "package_paths",
        "coverage_source",
        "file_length_paths",
        "vulture_paths",
        "pip_audit_args",
    }
    bool_fields = {"require_tests", "enable_pip_audit"}
    int_fields = {
        "coverage_fail_under",
        "diff_cover_fail_under",
        "file_length_max_physical",
        "file_length_max_source",
        "change_warn_lines",
        "change_block_lines",
        "change_warn_files",
        "change_block_files",
        "suppression_max_new",
        "ruff_max_complexity",
    }
    str_fields = {
        "xenon_max_absolute",
        "xenon_max_modules",
        "xenon_max_average",
        "pyright_type_checking_mode",
    }

    for field_name in tuple_fields:
        raw_value = raw.get(field_name)
        if raw_value is not None:
            updates[field_name] = _as_tuple(raw_value, field_name)
    for field_name in bool_fields:
        raw_value = raw.get(field_name)
        if raw_value is not None:
            updates[field_name] = _as_bool(raw_value, field_name)
    for field_name in int_fields:
        raw_value = raw.get(field_name)
        if raw_value is not None:
            updates[field_name] = _as_int(raw_value, field_name)
    for field_name in str_fields:
        raw_value = raw.get(field_name)
        if raw_value is not None:
            updates[field_name] = _as_str(raw_value, field_name)

    return replace(config, **updates)


def _env_tuple(name: str) -> tuple[str, ...] | None:
    value = os.getenv(name)
    if value is None:
        return None
    return _as_tuple(value, name)


def _env_bool(name: str) -> bool | None:
    value = os.getenv(name)
    if value is None:
        return None
    return _as_bool(value, name)


def _env_int(name: str) -> int | None:
    value = os.getenv(name)
    if value is None:
        return None
    return _as_int(value, name)


def _apply_env(config: GuardrailConfig) -> GuardrailConfig:
    updates: dict[str, object] = {}
    tuple_envs = {
        "source_roots": "GUARDRAILS_SOURCE_ROOTS",
        "test_roots": "GUARDRAILS_TEST_ROOTS",
        "package_paths": "GUARDRAILS_PACKAGE_PATHS",
        "coverage_source": "GUARDRAILS_COVERAGE_SOURCE",
        "file_length_paths": "GUARDRAILS_FILE_LENGTH_PATHS",
        "vulture_paths": "GUARDRAILS_VULTURE_PATHS",
    }
    for field_name, env_name in tuple_envs.items():
        value = _env_tuple(env_name)
        if value is not None:
            updates[field_name] = value

    require_tests = _env_bool("GUARDRAILS_REQUIRE_TESTS")
    if require_tests is not None:
        updates["require_tests"] = require_tests

    enable_pip_audit = _env_bool("GUARDRAILS_ENABLE_PIP_AUDIT")
    if enable_pip_audit is not None:
        updates["enable_pip_audit"] = enable_pip_audit

    coverage_fail_under = _env_int("GUARDRAILS_COVERAGE_FAIL_UNDER")
    if coverage_fail_under is not None:
        updates["coverage_fail_under"] = coverage_fail_under

    diff_cover_fail_under = _env_int("GUARDRAILS_DIFF_COVER_FAIL_UNDER")
    if diff_cover_fail_under is not None:
        updates["diff_cover_fail_under"] = diff_cover_fail_under

    threshold_envs = {
        "file_length_max_physical": "GUARDRAILS_FILE_LENGTH_MAX_PHYSICAL",
        "file_length_max_source": "GUARDRAILS_FILE_LENGTH_MAX_SOURCE",
        "change_warn_lines": "GUARDRAILS_CHANGE_WARN_LINES",
        "change_block_lines": "GUARDRAILS_CHANGE_BLOCK_LINES",
        "change_warn_files": "GUARDRAILS_CHANGE_WARN_FILES",
        "change_block_files": "GUARDRAILS_CHANGE_BLOCK_FILES",
        "suppression_max_new": "GUARDRAILS_SUPPRESSION_MAX_NEW",
    }
    for field_name, env_name in threshold_envs.items():
        value = _env_int(env_name)
        if value is not None:
            updates[field_name] = value

    pip_audit_args = os.getenv("GUARDRAILS_PIP_AUDIT_ARGS")
    if pip_audit_args is not None:
        updates["pip_audit_args"] = tuple(shlex.split(pip_audit_args))

    return replace(config, **updates)


def load_config() -> GuardrailConfig:
    config = GuardrailConfig()
    config = _apply_pyproject(config, _read_pyproject())
    config = _apply_env(config)
    return config


def existing_paths(paths: tuple[str, ...]) -> list[str]:
    return [path for path in paths if Path(path).exists()]


def any_path_exists(paths: tuple[str, ...]) -> bool:
    return any(Path(path).exists() for path in paths)


def format_paths(paths: tuple[str, ...]) -> str:
    return ", ".join(paths) if paths else "<none>"


def path_matches_roots(path: str, roots: tuple[str, ...]) -> bool:
    normalized = path.replace("\\", "/").lstrip("./")
    for root in roots:
        clean_root = root.replace("\\", "/").strip("/")
        if clean_root in {"", "."}:
            return True
        if normalized == clean_root or normalized.startswith(f"{clean_root}/"):
            return True
    return False
