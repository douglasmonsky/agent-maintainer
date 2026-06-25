#!/usr/bin/env python3
"""Shared configuration for the guardrail scripts.

Configuration precedence, lowest to highest:
1. Built-in defaults.
2. [tool.ai_guardrails].mode preset defaults.
3. Explicit [tool.ai_guardrails] fields in pyproject.toml.
4. GUARDRAILS_* environment variables.
5. Script-specific CLI overrides.
"""

from __future__ import annotations

import os
import shlex
from collections.abc import Callable
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
CUSTOM_MODE = "custom"
LEGACY_RATCHET_MODE = "legacy-ratchet"
FRESH_STRICT_MODE = "fresh-strict"
VALID_MODES = frozenset((CUSTOM_MODE, LEGACY_RATCHET_MODE, FRESH_STRICT_MODE))

TUPLE_FIELDS = frozenset(
    (
        "source_roots",
        "test_roots",
        "package_paths",
        "coverage_source",
        "file_length_paths",
        "vulture_paths",
        "pip_audit_args",
    )
)
BOOL_FIELDS = frozenset(("require_tests", "enable_pip_audit", "enable_wemake"))
INT_FIELDS = frozenset(
    (
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
    )
)
STR_FIELDS = frozenset(
    (
        "xenon_max_absolute",
        "xenon_max_modules",
        "xenon_max_average",
        "pyright_type_checking_mode",
    )
)


@dataclass(frozen=True)
class GuardrailConfig:
    mode: str = CUSTOM_MODE
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
    enable_wemake: bool = False
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


def _as_mode(value: object, field_name: str) -> str:
    mode = _as_str(value, field_name)
    if mode in VALID_MODES:
        return mode
    valid_modes = ", ".join(sorted(VALID_MODES))
    raise TypeError(f"{field_name} must be one of: {valid_modes}")


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
    mode_value = raw.get("mode")
    if mode_value is not None:
        config = apply_mode(config, _as_mode(mode_value, "mode"))
    return replace(config, **_coerce_updates(raw))


def _coerce_updates(raw: dict[str, Any]) -> dict[str, object]:
    updates: dict[str, object] = {}
    field_parsers = (
        (TUPLE_FIELDS, _as_tuple),
        (BOOL_FIELDS, _as_bool),
        (INT_FIELDS, _as_int),
        (STR_FIELDS, _as_str),
    )
    for fields, parser in field_parsers:
        for field_name in fields:
            raw_value = raw.get(field_name)
            if raw_value is not None:
                updates[field_name] = parser(raw_value, field_name)
    return updates


def apply_mode(config: GuardrailConfig, mode: str) -> GuardrailConfig:
    updates: dict[str, object] = {}
    if mode == LEGACY_RATCHET_MODE:
        updates = {
            "enable_pip_audit": False,
            "enable_wemake": False,
        }
    elif mode == FRESH_STRICT_MODE:
        updates = {
            "require_tests": True,
            "file_length_max_physical": 500,
            "file_length_max_source": 375,
            "change_warn_lines": 200,
            "change_block_lines": 600,
            "change_warn_files": 6,
            "change_block_files": 12,
            "suppression_max_new": 1,
            "ruff_max_complexity": 8,
            "enable_wemake": True,
        }
    return replace(config, mode=mode, **updates)


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


def _merge_env_values(
    updates: dict[str, object],
    envs: dict[str, str],
    parser: Callable[[str], object | None],
) -> None:
    for field_name, env_name in envs.items():
        parsed_value = parser(env_name)
        if parsed_value is not None:
            updates[field_name] = parsed_value


def _apply_env(config: GuardrailConfig) -> GuardrailConfig:
    mode = os.getenv("GUARDRAILS_MODE")
    if mode is not None:
        config = apply_mode(config, _as_mode(mode, "GUARDRAILS_MODE"))

    updates: dict[str, object] = {}
    tuple_envs = {
        "source_roots": "GUARDRAILS_SOURCE_ROOTS",
        "test_roots": "GUARDRAILS_TEST_ROOTS",
        "package_paths": "GUARDRAILS_PACKAGE_PATHS",
        "coverage_source": "GUARDRAILS_COVERAGE_SOURCE",
        "file_length_paths": "GUARDRAILS_FILE_LENGTH_PATHS",
        "vulture_paths": "GUARDRAILS_VULTURE_PATHS",
    }
    bool_envs = {
        "require_tests": "GUARDRAILS_REQUIRE_TESTS",
        "enable_pip_audit": "GUARDRAILS_ENABLE_PIP_AUDIT",
        "enable_wemake": "GUARDRAILS_ENABLE_WEMAKE",
    }
    coverage_envs = {
        "coverage_fail_under": "GUARDRAILS_COVERAGE_FAIL_UNDER",
        "diff_cover_fail_under": "GUARDRAILS_DIFF_COVER_FAIL_UNDER",
    }

    threshold_envs = {
        "file_length_max_physical": "GUARDRAILS_FILE_LENGTH_MAX_PHYSICAL",
        "file_length_max_source": "GUARDRAILS_FILE_LENGTH_MAX_SOURCE",
        "change_warn_lines": "GUARDRAILS_CHANGE_WARN_LINES",
        "change_block_lines": "GUARDRAILS_CHANGE_BLOCK_LINES",
        "change_warn_files": "GUARDRAILS_CHANGE_WARN_FILES",
        "change_block_files": "GUARDRAILS_CHANGE_BLOCK_FILES",
        "suppression_max_new": "GUARDRAILS_SUPPRESSION_MAX_NEW",
    }
    _merge_env_values(updates, tuple_envs, _env_tuple)
    _merge_env_values(updates, bool_envs, _env_bool)
    _merge_env_values(updates, coverage_envs, _env_int)
    _merge_env_values(updates, threshold_envs, _env_int)

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
