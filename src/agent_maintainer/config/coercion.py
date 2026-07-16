"""Coercion helpers for Agent Maintainer configuration values."""

from __future__ import annotations

import math
from dataclasses import fields, replace
from typing import Any, TypeGuard

from agent_maintainer.config import registry, schema, validation
from agent_maintainer.config.java import JavaReportExpectation

DEFAULT_CONFIG_SOURCE = "configuration"


def as_tuple(value: object, field_name: str) -> tuple[str, ...]:
    """Coerce a string or list-like value into a tuple of normalized paths."""

    items = _tuple_items(value, field_name)
    return tuple(item.rstrip("/") or "." for item in items if item)


def _tuple_items(value: object, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return tuple(part.strip() for part in value.split(","))
    if _is_object_sequence(value) and all(isinstance(part, str) for part in value):
        return tuple(part.strip() for part in value if isinstance(part, str))
    raise TypeError(f"{field_name} must be a string or list of strings")


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

    if isinstance(value, int) and not isinstance(value, bool):
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
        return _finite_float(float(value), field_name)
    if isinstance(value, str):
        try:
            return _finite_float(float(value), field_name)
        except ValueError as exc:
            raise TypeError(f"{field_name} must be a number") from exc
    raise TypeError(f"{field_name} must be a number")


def _finite_float(value: float, field_name: str) -> float:
    if math.isfinite(value):
        return value
    raise TypeError(f"{field_name} must be a finite number")


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


WORKSPACE_FIELD_PARSERS = tuple(
    (field_name, as_tuple) for field_name in sorted(registry.WORKSPACE_KEYS)
)


def coerce_file_baseline_group(
    name: str,
    raw_value: object,
    *,
    source: str = DEFAULT_CONFIG_SOURCE,
) -> schema.FileBaselineGroupConfig:
    """Coerce one named provider-neutral file baseline group."""
    if not name.strip():
        raise TypeError("file_baselines.groups name must not be empty")
    raw_group = _config_table(
        raw_value,
        f"file_baselines.groups.{name}",
    )
    validation.validate_raw_config(
        {"file_baselines": {"groups": {name: raw_group}}},
        source=source,
    )
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


def coerce_file_baselines(
    raw_value: object,
    *,
    source: str = DEFAULT_CONFIG_SOURCE,
) -> dict[str, object]:
    """Coerce nested provider-neutral file baseline config."""
    raw_table = _config_table(raw_value, "file_baselines")
    validation.validate_raw_config(
        {"file_baselines": raw_table},
        source=source,
    )
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
        group_table = _config_table(groups, "file_baselines.groups")
        updates["file_baselines"] = tuple(
            coerce_file_baseline_group(name, group, source=source)
            for name, group in sorted(group_table.items())
        )
    return updates


def coerce_workspace(
    name: str,
    raw_value: object,
    *,
    source: str = DEFAULT_CONFIG_SOURCE,
) -> schema.WorkspaceConfig:
    """Coerce one named workspace config table."""
    if not name.strip():
        raise TypeError("workspace name must not be empty")
    workspace = _config_table(raw_value, f"workspaces.{name}")
    validation.validate_raw_config(
        {"workspaces": {name: workspace}},
        source=source,
    )
    updates = {
        field_name: parser(workspace.get(field_name), f"workspaces.{name}.{field_name}")
        for field_name, parser in WORKSPACE_FIELD_PARSERS
    }
    return schema.WorkspaceConfig(name=name, **updates)


def coerce_workspaces(
    raw_value: object,
    *,
    source: str = DEFAULT_CONFIG_SOURCE,
) -> tuple[schema.WorkspaceConfig, ...]:
    """Coerce nested workspace config tables."""
    workspaces = _config_table(raw_value, "workspaces")
    return tuple(
        coerce_workspace(name, payload, source=source)
        for name, payload in sorted(workspaces.items())
    )


def coerce_diagnostics(
    raw_value: object,
    *,
    source: str = DEFAULT_CONFIG_SOURCE,
) -> dict[str, object]:
    """Coerce the nested diagnostics config table."""

    diagnostics = _config_table(raw_value, "diagnostics")
    validation.validate_raw_config(
        {"diagnostics": diagnostics},
        source=source,
    )
    updates: dict[str, object] = {}
    for raw_name, field_name in registry.DIAGNOSTIC_FIELD_MAP.items():
        value = diagnostics.get(raw_name)
        if value is not None:
            spec = registry.FIELD_SPECS[field_name]
            updates[field_name] = coerce_field_value(
                spec,
                value,
                f"diagnostics.{raw_name}",
                source=source,
            )
    return updates


def coerce_field_value(
    spec: registry.ConfigFieldSpec,
    value: object,
    field_name: str,
    *,
    source: str = DEFAULT_CONFIG_SOURCE,
) -> object:
    """Coerce and validate one value from its registry specification."""

    parsers = {
        "bool": as_bool,
        "float": as_float,
        "int": as_int,
        "non-negative-int": as_non_negative_int,
        "tuple": as_tuple,
    }
    if spec.value_kind == "choice":
        parsed = as_choice(value, field_name, spec.choices)
    elif spec.value_kind == "str":
        parsed = value if spec.allow_empty and isinstance(value, str) else as_str(value, field_name)
    else:
        parser = parsers.get(spec.value_kind)
        if parser is None:
            raise TypeError(f"{field_name} is not a scalar configuration field")
        parsed = parser(value, field_name)
    return validation.validate_field_value(parsed, spec, source=source)


def coerce_updates(
    raw: dict[str, Any],
    *,
    source: str = DEFAULT_CONFIG_SOURCE,
    prefix: str = validation.TOOL_TABLE,
) -> dict[str, object]:
    """Coerce raw pyproject config values into dataclass update values."""

    validation.validate_raw_config(raw, source=source, prefix=prefix)
    updates: dict[str, object] = {}
    for spec in registry.FIELD_SPECS.values():
        raw_item = _raw_scalar_item(raw, spec)
        if raw_item is None:
            continue
        raw_key, raw_value = raw_item
        if raw_value is not None:
            updates[spec.field_name] = coerce_field_value(
                spec,
                raw_value,
                raw_key,
                source=source,
            )
    workspaces = raw.get("workspaces")
    if workspaces is not None:
        updates["workspaces"] = coerce_workspaces(workspaces, source=source)
    diagnostics = raw.get("diagnostics")
    if diagnostics is not None:
        updates.update(coerce_diagnostics(diagnostics, source=source))
    file_baselines = raw.get("file_baselines")
    if file_baselines is not None:
        updates.update(coerce_file_baselines(file_baselines, source=source))
    java = raw.get("java")
    if java is not None:
        updates["java"] = coerce_java(java, source=source)
    return updates


def coerce_java(
    raw_value: object,
    *,
    source: str = DEFAULT_CONFIG_SOURCE,
) -> schema.JavaGradleConfig:
    """Coerce the provider-owned Java table without shell-like shortcuts."""

    raw = _config_table(raw_value, "java")
    validation.validate_raw_config({"java": raw}, source=source)
    defaults = schema.JavaGradleConfig()
    updates = _java_tuple_updates(raw, defaults)
    updates.update(_java_scalar_updates(raw))
    if "reports" in raw:
        updates["reports"] = _coerce_java_reports(raw["reports"], source=source)
    return replace(defaults, **updates)


def _java_tuple_updates(
    raw: dict[str, object],
    defaults: schema.JavaGradleConfig,
) -> dict[str, object]:
    tuple_fields = {
        field.name for field in fields(defaults) if isinstance(getattr(defaults, field.name), tuple)
    } - {"reports"}
    return {
        name: _java_string_tuple(raw[name], f"java.{name}")
        for name in sorted(tuple_fields)
        if name in raw
    }


def _java_scalar_updates(raw: dict[str, object]) -> dict[str, object]:
    updates: dict[str, object] = {}
    if "enabled" in raw:
        value = raw["enabled"]
        if not isinstance(value, bool):
            raise TypeError("java.enabled must be a boolean")
        updates["enabled"] = value
    for name in (
        "gradle_root",
        "spotless_ratchet_ref",
        "findings_baseline",
        "spotbugs_baseline",
        "jacoco_line_property",
        "jacoco_branch_property",
    ):
        if name in raw:
            value = raw[name]
            allow_empty = name in {"spotless_ratchet_ref", "spotbugs_baseline"}
            if not isinstance(value, str) or (not value and not allow_empty):
                raise TypeError(f"java.{name} must be a string")
            updates[name] = value
    return updates


def _coerce_java_reports(
    reports: object,
    *,
    source: str,
) -> tuple[JavaReportExpectation, ...]:
    if not isinstance(reports, list):
        raise TypeError("java.reports must be a list of tables")
    return tuple(
        _coerce_java_report(report, index=index, source=source)
        for index, report in enumerate(reports)
    )


def _coerce_java_report(
    raw_value: object,
    *,
    index: int,
    source: str,
) -> JavaReportExpectation:
    prefix = f"java.reports.{index}"
    raw = _config_table(raw_value, prefix)
    validation.validate_raw_config({"java": {"reports": [raw]}}, source=source)
    tool = raw.get("tool")
    if not isinstance(tool, str) or not tool:
        raise TypeError(f"{prefix}.tool must be a non-empty string")
    required = raw.get("required", True)
    if not isinstance(required, bool):
        raise TypeError(f"{prefix}.required must be a boolean")
    return JavaReportExpectation(
        tool=tool,
        tasks=_java_string_tuple(raw.get("tasks"), f"{prefix}.tasks"),
        globs=_java_string_tuple(raw.get("globs"), f"{prefix}.globs"),
        required=required,
    )


def _java_string_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise TypeError(f"{field_name} must be a list of strings")
    return tuple(value)


def _raw_scalar_item(
    raw: dict[str, Any],
    spec: registry.ConfigFieldSpec,
) -> tuple[str, object] | None:
    if spec.field_name in registry.NESTED_FIELD_KINDS:
        return None
    raw_keys = (
        spec.toml_aliases
        if spec.field_name in registry.NESTED_TOML_KEYS
        else (spec.toml_key, *spec.toml_aliases)
    )
    return next(
        ((key, raw[key]) for key in raw_keys if key in raw),
        None,
    )


def _config_table(value: object, label: str) -> dict[str, object]:
    """Return a string-keyed configuration table or fail with field context."""

    if not _is_object_table(value):
        raise TypeError(f"{label} must be a table")
    if not all(isinstance(key, str) for key in value):
        raise TypeError(f"{label} keys must be strings")
    return {key: item for key, item in value.items() if isinstance(key, str)}


def _is_object_sequence(value: object) -> TypeGuard[list[object] | tuple[object, ...]]:
    """Return whether value is a list or tuple with explicit element boundaries."""

    return isinstance(value, (list, tuple))


def _is_object_table(value: object) -> TypeGuard[dict[object, object]]:
    """Return whether value is a dictionary with explicit object boundaries."""

    return isinstance(value, dict)
