"""Tests low-level Agent Maintainer config coercion contracts."""

from __future__ import annotations

import pytest

from agent_maintainer.config import coercion, schema


@pytest.mark.parametrize("value", ("1", "true", "yes", "on", " YES ", "ON"))
def test_as_bool_accepts_documented_true_spellings(value: str) -> None:
    """Bool coercion accepts every documented true spelling."""

    assert coercion.as_bool(value, "enabled") is True


@pytest.mark.parametrize("value", ("0", "false", "no", "off", " NO ", "OFF"))
def test_as_bool_accepts_documented_false_spellings(value: str) -> None:
    """Bool coercion accepts every documented false spelling."""

    assert coercion.as_bool(value, "enabled") is False


def test_as_tuple_normalizes_paths_and_keeps_significant_suffixes() -> None:
    """Tuple coercion strips separators without stripping meaningful names."""

    assert coercion.as_tuple(["src/", "/", "docsX/", " tests ", ""], "paths") == (
        "src",
        ".",
        "docsX",
        "tests",
    )
    assert coercion.as_tuple("src/, tests/, ,docsX/", "paths") == (
        "src",
        "tests",
        "docsX",
    )


def test_as_non_negative_int_preserves_field_name_in_parse_errors() -> None:
    """Integer coercion errors name the field that failed."""

    with pytest.raises(TypeError, match="worker_count must be an integer"):
        coercion.as_non_negative_int(object(), "worker_count")


def test_as_choice_reports_sorted_valid_values_and_field_name() -> None:
    """Choice coercion errors include stable choices and field names."""

    with pytest.raises(TypeError, match="mode must be one of: alpha, beta"):
        coercion.as_choice("gamma", "mode", frozenset(("beta", "alpha")))


def test_as_choice_preserves_field_name_for_non_string_values() -> None:
    """Choice coercion delegates string validation with field context."""

    with pytest.raises(TypeError, match="mode"):
        coercion.as_choice(None, "mode", frozenset(("alpha", "beta")))


def test_coerce_diagnostics_preserves_nested_field_names() -> None:
    """Nested diagnostics parser errors point to the nested config key."""

    with pytest.raises(TypeError, match=r"diagnostics\.run_history_limit"):
        coercion.coerce_diagnostics({"run_history_limit": object()})


def test_coerce_updates_preserves_field_names_for_generic_parsers() -> None:
    """Top-level parser errors point to the original config key."""

    with pytest.raises(TypeError, match="coverage_fail_under"):
        coercion.coerce_updates({"coverage_fail_under": object()})


def test_coerce_updates_preserves_architecture_choice_context() -> None:
    """Architecture tool errors keep the public config field name."""

    with pytest.raises(TypeError, match="architecture_tool must be one of: import-linter, tach"):
        coercion.coerce_updates({"architecture_tool": "layers"})


def test_coerce_updates_loads_context_compression_backend() -> None:
    """Compression backend is explicitly read and constrained."""

    updates = coercion.coerce_updates(
        {"context_compression_backend": schema.EXTRACTIVE_COMPRESSION_BACKEND}
    )

    assert updates["context_compression_backend"] == schema.EXTRACTIVE_COMPRESSION_BACKEND


def test_coerce_updates_preserves_context_compression_backend_error_context() -> None:
    """Compression backend errors keep the public config field name."""

    with pytest.raises(TypeError, match=r"^context_compression_backend must be one of"):
        coercion.coerce_updates({"context_compression_backend": "external"})


def test_file_baseline_tables() -> None:
    """Top-level config coercion preserves nested file baseline tables."""
    updates = coercion.coerce_updates(
        {
            "file_baselines": {
                "enabled": True,
                "mode": "blocking",
                "groups": {
                    "docs": {
                        "include": ["docs/**/*.md"],
                        "role": "docs",
                    },
                },
            },
        },
    )

    assert (
        updates["file_baselines_enabled"],
        updates["file_baselines_mode"],
        updates["file_baselines"],
    ) == (
        True,
        "blocking",
        (
            schema.FileBaselineGroupConfig(
                name="docs",
                include=("docs/**/*.md",),
                role="docs",
            ),
        ),
    )


def test_file_baseline_group_fields() -> None:
    """File baseline group coercion preserves every public field."""
    group = coercion.coerce_file_baseline_group(
        "docs",
        {
            "include": ["docs/**/*.md"],
            "exclude": ["docs/generated/**"],
            "role": "docs",
            "max_physical_lines": 700,
            "max_nonblank_lines": 600,
            "changed_file_warn": 10,
            "changed_line_warn": 500,
        },
    )

    assert group == schema.FileBaselineGroupConfig(
        name="docs",
        include=("docs/**/*.md",),
        exclude=("docs/generated/**",),
        role="docs",
        max_physical_lines=700,
        max_nonblank_lines=600,
        changed_file_warn=10,
        changed_line_warn=500,
    )


def test_file_baseline_group_defaults_to_unknown_role() -> None:
    """File baseline groups use a stable default role when none configured."""
    group = coercion.coerce_file_baseline_group(
        "docs",
        {"include": ["docs/**/*.md"]},
    )

    assert group.role == "unknown"


@pytest.mark.parametrize(
    ("payload", "message"),
    (
        (
            {"enabled": object()},
            r"^file_baselines\.enabled must be a boolean",
        ),
        (
            {"mode": "external"},
            r"^file_baselines\.mode must be one of",
        ),
    ),
)
def test_file_baseline_table_errors(payload: object, message: str) -> None:
    """File baseline table coercion errors preserve public field names."""
    with pytest.raises(TypeError, match=message):
        coercion.coerce_file_baselines(payload)


@pytest.mark.parametrize(
    ("payload", "message"),
    (
        ({"include": 12}, r"file_baselines\.groups\.docs\.include"),
        ({"include": ["docs/**/*.md"], "exclude": 12}, r"file_baselines\.groups\.docs\.exclude"),
        ({"include": ["docs/**/*.md"], "role": object()}, r"file_baselines\.groups\.docs\.role"),
        (
            {"include": ["docs/**/*.md"], "max_physical_lines": object()},
            r"file_baselines\.groups\.docs\.max_physical_lines",
        ),
        (
            {"include": ["docs/**/*.md"], "max_nonblank_lines": object()},
            r"file_baselines\.groups\.docs\.max_nonblank_lines",
        ),
        (
            {"include": ["docs/**/*.md"], "changed_file_warn": object()},
            r"file_baselines\.groups\.docs\.changed_file_warn",
        ),
        (
            {"include": ["docs/**/*.md"], "changed_line_warn": object()},
            r"file_baselines\.groups\.docs\.changed_line_warn",
        ),
    ),
)
def test_file_baseline_group_errors(payload: object, message: str) -> None:
    """File baseline group coercion errors keep nested field names."""
    with pytest.raises(TypeError, match=message):
        coercion.coerce_file_baseline_group("docs", payload)
