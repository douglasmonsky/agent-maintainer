"""Coercion for the nested Java/Gradle provider configuration."""

from __future__ import annotations

from dataclasses import replace

from agent_maintainer.config import validation
from agent_maintainer.config.java import JavaGradleConfig, JavaReportExpectation
from agent_maintainer.core.structured_values import json_array, json_object

DEFAULT_CONFIG_SOURCE = "configuration"
JAVA_TUPLE_FIELDS = (
    "checks",
    "gradle_args",
    "source_roots",
    "test_roots",
    "spotless_tasks",
    "spotbugs_tasks",
    "checkstyle_tasks",
    "pmd_tasks",
    "test_tasks",
    "jacoco_report_tasks",
    "jacoco_verify_tasks",
    "spotless_profiles",
    "spotbugs_profiles",
    "checkstyle_profiles",
    "pmd_profiles",
    "test_profiles",
    "jacoco_profiles",
)


def _java_string_tuple(value: object, field_name: str) -> tuple[str, ...]:
    values = json_array(value)
    if values is None:
        raise TypeError(f"{field_name} must be a list of strings")
    strings = tuple(item for item in values if isinstance(item, str))
    if len(strings) != len(values):
        raise TypeError(f"{field_name} must be a list of strings")
    return strings


def _coerce_java_report(
    raw_value: object,
    *,
    index: int,
    source: str,
) -> JavaReportExpectation:
    prefix = f"java.reports.{index}"
    raw = _config_table(raw_value, prefix)
    validation.validate_raw_config({"java": {"reports": [raw]}}, source=source)
    tool = _value_or_default(raw, "tool", None)
    if not isinstance(tool, str) or not tool:
        raise TypeError(f"{prefix}.tool must be a non-empty string")
    required = _value_or_default(raw, "required", True)
    if not isinstance(required, bool):
        raise TypeError(f"{prefix}.required must be a boolean")
    return JavaReportExpectation(
        tool=tool,
        tasks=_java_string_tuple(_value_or_default(raw, "tasks", None), f"{prefix}.tasks"),
        globs=_java_string_tuple(_value_or_default(raw, "globs", None), f"{prefix}.globs"),
        required=required,
    )


def _coerce_java_reports(
    reports: object,
    *,
    source: str,
) -> tuple[JavaReportExpectation, ...]:
    values = json_array(reports)
    if values is None:
        raise TypeError("java.reports must be a list of tables")
    return tuple(
        _coerce_java_report(report, index=index, source=source)
        for index, report in enumerate(values)
    )


def _java_scalar_updates(raw: dict[str, object]) -> dict[str, object]:
    updates: dict[str, object] = {}
    if "enabled" in raw:
        value = _required_value(raw, "enabled")
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
            value = _required_value(raw, name)
            allow_empty = name in {"spotless_ratchet_ref", "spotbugs_baseline"}
            if not isinstance(value, str) or (not value and not allow_empty):
                raise TypeError(f"java.{name} must be a string")
            updates[name] = value
    return updates


def coerce_java(
    raw_value: object,
    *,
    source: str = DEFAULT_CONFIG_SOURCE,
) -> JavaGradleConfig:
    """Coerce the provider-owned Java table without shell-like shortcuts."""

    raw = _config_table(raw_value, "java")
    validation.validate_raw_config({"java": raw}, source=source)
    defaults = JavaGradleConfig()
    updates = _java_tuple_updates(raw)
    updates.update(_java_scalar_updates(raw))
    if "reports" in raw:
        updates["reports"] = _coerce_java_reports(
            _required_value(raw, "reports"),
            source=source,
        )
    return replace(defaults, **updates)


def _java_tuple_updates(raw: dict[str, object]) -> dict[str, object]:
    return {
        name: _java_string_tuple(raw[name], f"java.{name}")
        for name in JAVA_TUPLE_FIELDS
        if name in raw
    }


def _config_table(value: object, label: str) -> dict[str, object]:
    table = json_object(value)
    if table is None:
        raise TypeError(f"{label} must be a table")
    return table


def _value_or_default(
    raw: dict[str, object],
    key: str,
    default: object,
) -> object:
    try:
        return raw[key]
    except KeyError:
        return default


def _required_value(raw: dict[str, object], key: str) -> object:
    return raw[key]
