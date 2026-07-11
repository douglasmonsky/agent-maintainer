"""Fail-closed validation for raw and resolved Agent Maintainer configuration."""

from __future__ import annotations

import math
from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import cast

from agent_maintainer import models
from agent_maintainer.config import registry, schema, source_validation, value_types
from agent_maintainer.config.issues import ConfigIssue, ConfigValidationError

TOOL_TABLE = source_validation.TOOL_TABLE


def known_top_level_keys() -> frozenset[str]:
    """Return supported top-level keys from the field registry."""

    return source_validation.known_top_level_keys()


def known_diagnostic_keys() -> frozenset[str]:
    """Return supported keys under the diagnostics table."""

    return source_validation.known_diagnostic_keys()


def unknown_keys(raw: dict[str, object], *, prefix: str = TOOL_TABLE) -> tuple[str, ...]:
    """Return unknown top-level and nested key paths deterministically."""

    return source_validation.unknown_keys(raw, prefix=prefix)


def validate_raw_config(
    raw: dict[str, object],
    *,
    source: str,
    prefix: str = TOOL_TABLE,
) -> None:
    """Reject unknown raw keys before coercion can drop them."""

    source_validation.validate_raw_config(raw, source=source, prefix=prefix)


def validate_environment_names(environment: Mapping[str, str]) -> None:
    """Reject unknown Agent Maintainer environment variables."""

    source_validation.validate_environment_names(environment)


def validate_config(
    config: schema.MaintainerConfig,
    *,
    source: str = "merged configuration",
) -> schema.MaintainerConfig:
    """Validate the complete resolved policy and return it unchanged."""

    issues = [
        issue
        for spec in registry.FIELD_SPECS.values()
        for issue in _field_issues(config, spec, source=source)
    ]
    issues.extend(_workspace_issues(config, source=source))
    issues.extend(_file_baseline_issues(config, source=source))
    issues.extend(_cross_field_issues(config, source=source))
    if issues:
        raise ConfigValidationError(tuple(issues))
    return config


def validate_field_value(
    value: object,
    spec: registry.ConfigFieldSpec,
    *,
    source: str,
) -> object:
    """Validate one coerced registry value before it enters an update map."""

    issues = list(_constraint_issues(value, spec, source=source))
    if spec.path_value:
        issues.extend(_path_issues(value, spec, source=source))
    if spec.profile_values:
        issues.extend(_profile_issues(value, spec, source=source))
    if issues:
        raise ConfigValidationError(tuple(issues))
    return value


def _field_issues(
    config: schema.MaintainerConfig,
    spec: registry.ConfigFieldSpec,
    *,
    source: str,
) -> tuple[ConfigIssue, ...]:
    value = getattr(config, spec.field_name)
    if spec.value_kind in {"workspaces", "file-baseline-groups"}:
        return ()
    type_message = value_types.type_message(value, spec)
    if type_message:
        return (ConfigIssue(source, spec.toml_key, type_message),)
    issues = list(_constraint_issues(value, spec, source=source))
    if spec.path_value:
        issues.extend(_path_issues(value, spec, source=source))
    if spec.profile_values:
        issues.extend(_profile_issues(value, spec, source=source))
    return tuple(issues)


def _constraint_issues(
    value: object,
    spec: registry.ConfigFieldSpec,
    *,
    source: str,
) -> tuple[ConfigIssue, ...]:
    issues: list[ConfigIssue] = []
    if spec.choices and isinstance(value, str) and value not in spec.choices:
        choices = ", ".join(sorted(spec.choices))
        issues.append(ConfigIssue(source, spec.toml_key, f"must be one of: {choices}"))
    if isinstance(value, (float, int)) and not isinstance(value, bool):
        issues.extend(_numeric_issues(float(value), spec, source=source))
    return tuple(issues)


def _numeric_issues(
    value: float,
    spec: registry.ConfigFieldSpec,
    *,
    source: str,
) -> tuple[ConfigIssue, ...]:
    if not math.isfinite(value):
        return (ConfigIssue(source, spec.toml_key, "must be finite"),)
    minimum = spec.minimum
    if minimum is not None and (value < minimum or (spec.minimum_exclusive and value == minimum)):
        relation = "greater than" if spec.minimum_exclusive else "at least"
        minimum_text = format(minimum, "g")
        return (ConfigIssue(source, spec.toml_key, f"must be {relation} {minimum_text}"),)
    maximum = spec.maximum
    if maximum is not None and value > maximum:
        maximum_text = format(maximum, "g")
        return (ConfigIssue(source, spec.toml_key, f"must be at most {maximum_text}"),)
    return ()


def _path_issues(
    value: object,
    spec: registry.ConfigFieldSpec,
    *,
    source: str,
) -> tuple[ConfigIssue, ...]:
    values = cast(tuple[object, ...], value) if isinstance(value, tuple) else (value,)
    return tuple(
        ConfigIssue(source, spec.toml_key, f"must be repository-relative without '..': {item}")
        for item in values
        if isinstance(item, str) and item and not _is_repo_relative(item)
    )


def _is_repo_relative(value: str) -> bool:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    has_drive = normalized[1:].startswith(":/")
    return (
        not path.is_absolute()
        and not has_drive
        and not normalized.startswith("~")
        and ".." not in path.parts
    )


def _nested_path_issues(
    values: tuple[str, ...],
    *,
    key: str,
    source: str,
) -> tuple[ConfigIssue, ...]:
    return tuple(
        ConfigIssue(source, key, f"must be repository-relative without '..': {item}")
        for item in values
        if item and not _is_repo_relative(item)
    )


def _profile_issues(
    value: object,
    spec: registry.ConfigFieldSpec,
    *,
    source: str,
) -> tuple[ConfigIssue, ...]:
    values = cast(tuple[object, ...], value) if isinstance(value, tuple) else ()
    return tuple(
        ConfigIssue(source, spec.toml_key, f"unknown verification profile: {profile}")
        for profile in values
        if profile not in models.VALID_PROFILES
    )


def _workspace_issues(
    config: schema.MaintainerConfig,
    *,
    source: str,
) -> tuple[ConfigIssue, ...]:
    issues: list[ConfigIssue] = []
    names: set[str] = set()
    for workspace in config.workspaces:
        prefix = f"workspaces.{workspace.name}"
        if not workspace.name.strip() or workspace.name in names:
            issues.append(
                ConfigIssue(source, prefix, "workspace name must be non-empty and unique")
            )
        names.add(workspace.name)
        for field_name in registry.WORKSPACE_PATH_KEYS:
            value = getattr(workspace, field_name)
            issues.extend(_nested_path_issues(value, key=f"{prefix}.{field_name}", source=source))
    return tuple(issues)


def _file_baseline_issues(
    config: schema.MaintainerConfig,
    *,
    source: str,
) -> tuple[ConfigIssue, ...]:
    issues: list[ConfigIssue] = []
    names: set[str] = set()
    for group in config.file_baselines:
        prefix = f"file_baselines.groups.{group.name}"
        if not group.name.strip() or group.name in names:
            issues.append(ConfigIssue(source, prefix, "group name must be non-empty and unique"))
        names.add(group.name)
        if not group.include:
            issues.append(ConfigIssue(source, f"{prefix}.include", "must not be empty"))
        for field_name in ("include", "exclude"):
            issues.extend(
                _nested_path_issues(
                    getattr(group, field_name),
                    key=f"{prefix}.{field_name}",
                    source=source,
                )
            )
        for field_name in (
            "max_physical_lines",
            "max_nonblank_lines",
            "changed_file_warn",
            "changed_line_warn",
        ):
            value = getattr(group, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                issues.append(ConfigIssue(source, f"{prefix}.{field_name}", "must be non-negative"))
    return tuple(issues)


def _cross_field_issues(
    config: schema.MaintainerConfig,
    *,
    source: str,
) -> tuple[ConfigIssue, ...]:
    ordered_pairs = (
        ("change_warn_lines", "change_block_lines"),
        ("change_warn_files", "change_block_files"),
        ("folder_file_warn", "folder_file_block"),
        ("file_length_max_source", "file_length_max_physical"),
    )
    issues = [
        ConfigIssue(source, upper, f"must be greater than or equal to {lower}")
        for lower, upper in ordered_pairs
        if getattr(config, lower) > getattr(config, upper)
    ]
    if config.context_compression_require_backend and not config.context_compression_enabled:
        issues.append(
            ConfigIssue(
                source,
                "context_compression_require_backend",
                "requires context_compression_enabled = true",
            )
        )
    if config.context_compression_enabled and config.context_compression_backend == "none":
        issues.append(
            ConfigIssue(
                source,
                "context_compression_backend",
                "cannot be 'none' when compression is enabled",
            )
        )
    return tuple(issues)
