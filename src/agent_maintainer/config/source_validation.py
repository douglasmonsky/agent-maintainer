"""Fail-closed validation for raw configuration source names."""

from __future__ import annotations

from collections.abc import Mapping

from agent_maintainer.config import registry
from agent_maintainer.config.issues import ConfigIssue, ConfigValidationError
from agent_maintainer.core.structured_values import json_object

TOOL_TABLE = "tool.agent_maintainer"


def known_top_level_keys() -> frozenset[str]:
    """Return supported top-level keys from the field registry."""

    return registry.top_level_toml_keys()


def known_diagnostic_keys() -> frozenset[str]:
    """Return supported keys under the diagnostics table."""

    return registry.DIAGNOSTIC_KEYS


def unknown_keys(raw: dict[str, object], *, prefix: str = TOOL_TABLE) -> tuple[str, ...]:
    """Return unknown top-level and nested key paths deterministically."""

    unknown = [f"{prefix}.{key}" for key in raw if key not in known_top_level_keys()]
    unknown.extend(_unknown_fixed_table(raw, "diagnostics", registry.DIAGNOSTIC_KEYS, prefix))
    unknown.extend(_unknown_dynamic_table(raw, "workspaces", registry.WORKSPACE_KEYS, prefix))
    unknown.extend(_unknown_file_baselines(raw, prefix=prefix))
    return tuple(sorted(unknown))


def validate_raw_config(
    raw: dict[str, object],
    *,
    source: str,
    prefix: str = TOOL_TABLE,
) -> None:
    """Reject unknown raw keys before coercion can drop them."""

    issues = [
        ConfigIssue(source, key, "unknown configuration key")
        for key in unknown_keys(raw, prefix=prefix)
    ]
    issues.extend(_alias_conflict_issues(raw, source=source, prefix=prefix))
    if issues:
        raise ConfigValidationError(tuple(issues))


def validate_environment_names(environment: Mapping[str, str]) -> None:
    """Reject unknown Agent Maintainer environment variables."""

    known = registry.known_environment_names()
    issues = tuple(
        ConfigIssue("environment", name, "unknown Agent Maintainer environment variable")
        for name in sorted(environment)
        if name.startswith("AGENT_MAINTAINER_") and name not in known
    )
    if issues:
        raise ConfigValidationError(issues)


def _unknown_fixed_table(
    raw: dict[str, object],
    table_name: str,
    allowed: frozenset[str],
    prefix: str,
) -> tuple[str, ...]:
    value = json_object(raw.get(table_name))
    if value is None:
        return ()
    return tuple(f"{prefix}.{table_name}.{key}" for key in value if key not in allowed)


def _unknown_dynamic_table(
    raw: dict[str, object],
    table_name: str,
    allowed: frozenset[str],
    prefix: str,
) -> tuple[str, ...]:
    value = json_object(raw.get(table_name))
    if value is None:
        return ()
    return tuple(
        f"{prefix}.{table_name}.{name}.{key}"
        for name, payload in value.items()
        if (nested := json_object(payload)) is not None
        for key in nested
        if key not in allowed
    )


def _unknown_file_baselines(raw: dict[str, object], *, prefix: str) -> tuple[str, ...]:
    value = json_object(raw.get("file_baselines"))
    if value is None:
        return ()
    unknown = [
        f"{prefix}.file_baselines.{key}" for key in value if key not in registry.FILE_BASELINE_KEYS
    ]
    groups = json_object(value.get("groups"))
    if groups is not None:
        unknown.extend(
            f"{prefix}.file_baselines.groups.{name}.{key}"
            for name, payload in groups.items()
            if (nested := json_object(payload)) is not None
            for key in nested
            if key not in registry.FILE_BASELINE_GROUP_KEYS
        )
    return tuple(unknown)


def _alias_conflict_issues(
    raw: dict[str, object],
    *,
    source: str,
    prefix: str,
) -> tuple[ConfigIssue, ...]:
    return tuple(
        ConfigIssue(
            source,
            f"{prefix}.{alias}",
            f"cannot be combined with {prefix}.{spec.toml_key}",
        )
        for spec in registry.FIELD_SPECS.values()
        for alias in spec.toml_aliases
        if alias in raw and _has_nested_value(raw, spec.toml_key)
    )


def _has_nested_value(raw: dict[str, object], dotted_key: str) -> bool:
    table_name, separator, key = dotted_key.partition(".")
    table = raw.get(table_name)
    return bool(separator and isinstance(table, dict) and key in table)
