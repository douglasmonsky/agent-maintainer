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

    with pytest.raises(TypeError, match="context_compression_backend"):
        coercion.coerce_updates({"context_compression_backend": "external"})
