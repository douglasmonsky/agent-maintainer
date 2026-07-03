"""Coercion helpers for Agent Maintainer configuration values."""

from __future__ import annotations

from typing import Any

from agent_maintainer.config import schema


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


def as_non_negative_int(value: object, field_name: str) -> int:
    """Coerce an integer config value that cannot be negative."""

    parsed = as_int(value, field_name)
    if parsed < 0:
        raise TypeError(f"{field_name} must be a non-negative integer")
    return parsed


def as_float(value: object, field_name: str) -> float:
    """Coerce a float config value."""

    if isinstance(value, bool):
        raise TypeError(f"{field_name} must be a number")
    if isinstance(value, (float, int)):
        return float(value)
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a number")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{field_name} must be a number") from exc


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
    ("run_history_limit", "diagnostic_run_history_limit", as_non_negative_int),
)


WORKSPACE_FIELD_PARSERS = (
    ("source_roots", as_tuple),
    ("test_roots", as_tuple),
    ("package_paths", as_tuple),
    ("coverage_source", as_tuple),
)


def coerce_file_baseline_group(
    name: str,
    raw_value: object,
) -> schema.FileBaselineGroupConfig:
    """Coerce one named provider-neutral file baseline group."""
    if not name.strip():
        raise TypeError("file_baselines.groups name must not be empty")
    if not isinstance(raw_value, dict):
        raise TypeError(f"file_baselines.groups.{name} must be a table")
    raw_group: dict[str, object] = raw_value
    include = as_tuple(raw_group.get("include"), f"file_baselines.groups.{name}.include")
    if not include:
        raise TypeError(f"file_baselines.groups.{name}.include must not be empty")
    role_value = raw_group.get("role", "unknown")
    return schema.FileBaselineGroupConfig(
        name=name,
        include=include,
        exclude=as_tuple(raw_group.get("exclude"), f"file_baselines.groups.{name}.exclude"),
        role=as_str(role_value, f"file_baselines.groups.{name}.role"),
        max_physical_lines=as_non_negative_int(
            raw_group.get("max_physical_lines", 0),
            f"file_baselines.groups.{name}.max_physical_lines",
        ),
        max_nonblank_lines=as_non_negative_int(
            raw_group.get("max_nonblank_lines", 0),
            f"file_baselines.groups.{name}.max_nonblank_lines",
        ),
        changed_file_warn=as_non_negative_int(
            raw_group.get("changed_file_warn", 0),
            f"file_baselines.groups.{name}.changed_file_warn",
        ),
        changed_line_warn=as_non_negative_int(
            raw_group.get("changed_line_warn", 0),
            f"file_baselines.groups.{name}.changed_line_warn",
        ),
    )


def coerce_file_baselines(raw_value: object) -> dict[str, object]:
    """Coerce nested provider-neutral file baseline config."""
    if not isinstance(raw_value, dict):
        raise TypeError("file_baselines must be a table")
    raw_table: dict[str, object] = raw_value
    updates: dict[str, object] = {}
    enabled = raw_table.get("enabled")
    if enabled is not None:
        updates["file_baselines_enabled"] = as_bool(enabled, "file_baselines.enabled")
    mode = raw_table.get("mode")
    if mode is not None:
        updates["file_baselines_mode"] = as_choice(
            mode,
            "file_baselines.mode",
            schema.VALID_FILE_BASELINE_MODES,
        )
    groups = raw_table.get("groups")
    if groups is not None:
        if not isinstance(groups, dict):
            raise TypeError("file_baselines.groups must be a table")
        group_table: dict[str, object] = groups
        updates["file_baselines"] = tuple(
            coerce_file_baseline_group(name, group) for name, group in sorted(group_table.items())
        )
    return updates


def coerce_workspace(
    name: str,
    raw_value: object,
) -> schema.WorkspaceConfig:
    """Coerce one named workspace config table."""
    if not name.strip():
        raise TypeError("workspace name must not be empty")
    if not isinstance(raw_value, dict):
        raise TypeError(f"workspaces.{name} must be a table")
    updates = {
        field_name: parser(raw_value.get(field_name), f"workspaces.{name}.{field_name}")
        for field_name, parser in WORKSPACE_FIELD_PARSERS
    }
    return schema.WorkspaceConfig(name=name, **updates)


def coerce_workspaces(raw_value: object) -> tuple[schema.WorkspaceConfig, ...]:
    """Coerce nested workspace config tables."""
    if not isinstance(raw_value, dict):
        raise TypeError("workspaces must be a table")
    return tuple(coerce_workspace(name, payload) for name, payload in sorted(raw_value.items()))


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


def coerce_updates(raw: dict[str, Any]) -> dict[str, object]:  # noqa: C901
    """Coerce raw pyproject config values into dataclass update values."""

    updates: dict[str, object] = {}
    field_parsers = (
        (schema.TUPLE_FIELDS, as_tuple),
        (schema.BOOL_FIELDS, as_bool),
        (schema.NON_NEGATIVE_INT_FIELDS, as_non_negative_int),
        (schema.INT_FIELDS, as_int),
        (schema.FLOAT_FIELDS, as_float),
        (schema.STR_FIELDS, as_str),
    )
    for fields, parser in field_parsers:
        for field_name in fields:
            raw_value = raw.get(field_name)
            if raw_value is not None:
                updates[field_name] = parser(raw_value, field_name)
    workspaces = raw.get("workspaces")
    if workspaces is not None:
        updates["workspaces"] = coerce_workspaces(workspaces)
    architecture_tool = raw.get("architecture_tool")
    if architecture_tool is not None:
        updates["architecture_tool"] = as_choice(
            architecture_tool, "architecture_tool", schema.VALID_ARCHITECTURE_TOOLS
        )
    compression_backend = raw.get("context_compression_backend")
    if compression_backend is not None:
        updates["context_compression_backend"] = as_choice(
            compression_backend,
            "context_compression_backend",
            schema.VALID_CONTEXT_COMPRESSION_BACKENDS,
        )
    diagnostics = raw.get("diagnostics")
    if diagnostics is not None:
        updates.update(coerce_diagnostics(diagnostics))
    file_baselines = raw.get("file_baselines")
    if file_baselines is not None:
        updates.update(coerce_file_baselines(file_baselines))
    return updates
