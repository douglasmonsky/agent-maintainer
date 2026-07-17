"""Load and validate Agent Maintainer configuration from every public source."""

from __future__ import annotations

import os
import shlex
import tomllib
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from agent_maintainer.config import coercion, modes, registry, schema, validation
from agent_maintainer.core.structured_values import json_object

NEUTRAL_CONFIG_PATHS = (
    Path(".agent-maintainer/config.toml"),
    Path("agent-maintainer.toml"),
)
NEUTRAL_PREFIX = "agent_maintainer"


def _env_pairs(fields: frozenset[str]) -> tuple[tuple[str, str], ...]:
    return tuple(
        (field_name, registry.FIELD_SPECS[field_name].env_var) for field_name in sorted(fields)
    )


TUPLE_ENVS = _env_pairs(registry.TUPLE_ENV_FIELDS)
BOOL_ENVS = _env_pairs(registry.BOOL_ENV_FIELDS)
NON_NEGATIVE_INT_ENVS = _env_pairs(registry.NON_NEGATIVE_INT_FIELDS)
FLOAT_ENVS = _env_pairs(registry.FLOAT_FIELDS)
COVERAGE_ENVS = _env_pairs(frozenset(("coverage_fail_under", "diff_cover_fail_under")))
THRESHOLD_ENVS = _env_pairs(
    registry.INT_ENV_FIELDS - frozenset(("coverage_fail_under", "diff_cover_fail_under"))
)
STRING_ENVS = _env_pairs(registry.STRING_ENV_FIELDS)
SHELL_ENVS = _env_pairs(registry.SHELL_ENV_FIELDS)
SPECIAL_ENVS = _env_pairs(registry.SPECIAL_ENV_FIELDS)


@dataclass(frozen=True)
class ConfigDocument:
    """One located raw configuration document and its public key prefix."""

    raw: dict[str, object]
    source: str
    prefix: str


def _read_toml(path: Path) -> dict[str, object]:
    """Read one TOML document with source-aware parse failures."""

    if not path.exists():
        return {}
    try:
        with path.open("rb") as handle:
            payload: object = tomllib.load(handle)
            return json_object(payload) or {}
    except (OSError, tomllib.TOMLDecodeError) as exc:
        issue = validation.ConfigIssue(str(path), "<document>", f"invalid TOML: {exc}")
        raise validation.ConfigValidationError((issue,)) from exc


def read_pyproject(path: Path | None = None) -> dict[str, object]:
    """Read `[tool.agent_maintainer]` from pyproject.toml."""

    selected = path or Path("pyproject.toml")
    return _pyproject_config(_read_toml(selected), source=str(selected))


def _pyproject_config(payload: dict[str, object], *, source: str) -> dict[str, object]:
    raw_tool = payload.get("tool")
    if raw_tool is None:
        return {}
    tool = json_object(raw_tool)
    if tool is None:
        raise _shape_error(source, "tool", "must be a table")
    raw_config = tool.get("agent_maintainer")
    if raw_config is None:
        return {}
    config = json_object(raw_config)
    if config is None:
        raise _shape_error(source, validation.TOOL_TABLE, "must be a table")
    return config


def read_neutral_config(
    paths: tuple[Path, ...] = NEUTRAL_CONFIG_PATHS,
) -> dict[str, object]:
    """Read the first present neutral Agent Maintainer config file."""

    for path in paths:
        payload = _read_toml(path)
        if payload:
            return payload
    return {}


def read_config_document(repo_root: Path | None = None) -> ConfigDocument:
    """Locate the winning file-based configuration and retain its source."""

    root = Path.cwd() if repo_root is None else repo_root
    pyproject_path = root / "pyproject.toml"
    pyproject = read_pyproject(pyproject_path)
    if pyproject:
        return ConfigDocument(
            pyproject,
            f"{pyproject_path}:[tool.agent_maintainer]",
            validation.TOOL_TABLE,
        )
    for relative in NEUTRAL_CONFIG_PATHS:
        path = root / relative
        payload = _read_toml(path)
        if payload:
            return ConfigDocument(payload, str(path), NEUTRAL_PREFIX)
    return ConfigDocument({}, "defaults", validation.TOOL_TABLE)


def read_config(repo_root: Path | None = None) -> dict[str, object]:
    """Read file-based config with deterministic source precedence."""

    return read_config_document(repo_root).raw


def apply_pyproject(
    config: schema.MaintainerConfig,
    raw: dict[str, Any],
    *,
    source: str = "configuration",
    prefix: str = validation.TOOL_TABLE,
) -> schema.MaintainerConfig:
    """Apply one raw document after validating all keys and values."""

    try:
        resolved = _apply_raw_document(config, raw, source=source, prefix=prefix)
    except validation.ConfigValidationError:
        raise
    except TypeError as exc:
        raise _coercion_error(source, exc) from exc
    return validation.validate_config(resolved, source=source)


def _apply_raw_document(
    config: schema.MaintainerConfig,
    raw: dict[str, Any],
    *,
    source: str,
    prefix: str,
) -> schema.MaintainerConfig:
    validation.validate_raw_config(raw, source=source, prefix=prefix)
    mode_value = raw.get("mode")
    if mode_value is not None:
        mode_spec = registry.FIELD_SPECS["mode"]
        mode = coercion.coerce_field_value(
            mode_spec,
            mode_value,
            mode_spec.toml_key,
            source=source,
        )
        config = modes.apply_mode(config, str(mode))
    updates = coercion.coerce_updates(raw, source=source, prefix=prefix)
    return replace(config, **updates)


def env_value(
    env_name: str,
    parser: Callable[[object, str], object],
    *,
    environment: Mapping[str, str] | None = None,
) -> object | None:
    """Return one parsed environment value when present."""

    current = os.environ if environment is None else environment
    if env_name not in current:
        return None
    return parser(current[env_name], env_name)


def merge_env_values(
    updates: dict[str, object],
    envs: tuple[tuple[str, str], ...],
    parser: Callable[[object, str], object],
    *,
    environment: Mapping[str, str] | None = None,
) -> None:
    """Compatibility helper for merging a homogeneous environment group."""

    for field_name, env_name in envs:
        parsed_value = env_value(env_name, parser, environment=environment)
        if parsed_value is not None:
            updates[field_name] = parsed_value


def apply_env(
    config: schema.MaintainerConfig,
    *,
    environment: Mapping[str, str] | None = None,
) -> schema.MaintainerConfig:
    """Apply every registered environment override and validate the result."""

    current = os.environ if environment is None else environment
    validation.validate_environment_names(current)
    mode_spec = registry.FIELD_SPECS["mode"]
    mode_raw = current.get(mode_spec.env_var)
    if mode_raw is not None:
        mode = _coerce_env_value(mode_spec, mode_raw)
        config = modes.apply_mode(config, str(mode))
    updates = {
        spec.field_name: _coerce_env_value(spec, current[spec.env_var])
        for spec in registry.env_specs()
        if spec.field_name not in {"mode", "java"} and spec.env_var in current
    }
    java_enabled = current.get(registry.JAVA_ENABLED_ENV)
    if java_enabled is not None:
        updates["java"] = replace(
            config.java,
            enabled=coercion.as_bool(java_enabled, registry.JAVA_ENABLED_ENV),
        )
    resolved = replace(config, **updates)
    return validation.validate_config(resolved, source="merged file/environment configuration")


def _coerce_env_value(spec: registry.ConfigFieldSpec, raw_value: str) -> object:
    try:
        return _parse_env_value(spec, raw_value)
    except validation.ConfigValidationError:
        raise
    except ValueError as exc:
        issue = validation.ConfigIssue(
            "environment",
            spec.env_var,
            f"invalid shell syntax: {exc}",
        )
        raise validation.ConfigValidationError((issue,)) from exc
    except TypeError as exc:
        raise _coercion_error("environment", exc) from exc


def _parse_env_value(spec: registry.ConfigFieldSpec, raw_value: str) -> object:
    if spec.env_style == "shell":
        value: object = tuple(shlex.split(raw_value))
        return validation.validate_field_value(value, spec, source="environment")
    return coercion.coerce_field_value(
        spec,
        raw_value,
        spec.env_var,
        source="environment",
    )


def load_config(repo_root: Path | None = None) -> schema.MaintainerConfig:
    """Load one complete fail-closed configuration from all sources."""

    document = read_config_document(repo_root)
    config = apply_pyproject(
        schema.MaintainerConfig(),
        document.raw,
        source=document.source,
        prefix=document.prefix,
    )
    return apply_env(config)


def _shape_error(source: str, key: str, message: str) -> validation.ConfigValidationError:
    return validation.ConfigValidationError((validation.ConfigIssue(source, key, message),))


def _coercion_error(source: str, exc: TypeError) -> validation.ConfigValidationError:
    text = str(exc)
    key = text.split(" must", 1)[0]
    message = text.removeprefix(key).lstrip(": ") or "invalid value"
    return validation.ConfigValidationError((validation.ConfigIssue(source, key, message),))
