"""Tests configuration metadata drift guards."""

from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

from agent_maintainer.config import loader, metadata, schema

ARGS_MODULE = Path("src/agent_maintainer/core/args.py")


def test_every_config_field_has_metadata() -> None:
    """Metadata covers every maintained config field."""
    field_names = {field.name for field in fields(schema.MaintainerConfig)}

    assert set(metadata.FIELD_METADATA) == field_names
    for field_name, field_metadata in metadata.FIELD_METADATA.items():
        assert field_metadata.field_name == field_name
        assert field_metadata.toml_key
        assert field_metadata.docs_label
        assert field_metadata.cli_override in metadata.VALID_CLI_OVERRIDE_STATUSES
        assert field_metadata.stability in metadata.VALID_STABILITY_LEVELS


def test_metadata_env_vars_match_loader_env_maps() -> None:
    """Metadata environment override coverage stays aligned with loader."""
    expected_env_vars = metadata.env_vars_by_field()

    assert expected_env_vars == loader_env_vars_by_field()
    for field_name, field_metadata in metadata.FIELD_METADATA.items():
        assert field_metadata.env_var == expected_env_vars.get(field_name, "")


def test_diagnostic_fields_record_nested_toml_keys() -> None:
    """Nested diagnostics table fields advertise their public TOML paths."""
    assert metadata.FIELD_METADATA["diagnostic_artifacts_enabled"].toml_key == "diagnostics.enabled"
    assert metadata.FIELD_METADATA["diagnostic_artifacts_dir"].toml_key == "diagnostics.log_dir"
    assert (
        metadata.FIELD_METADATA["diagnostic_run_history_limit"].toml_key
        == "diagnostics.run_history_limit"
    )


def test_metadata_cli_override_fields_match_verify_cli() -> None:
    """CLI override metadata matches fields actually used by verifier CLI."""
    cli_override_fields = {
        field_name
        for field_name, field_metadata in metadata.FIELD_METADATA.items()
        if field_metadata.has_cli_override
    }

    assert cli_override_fields == implemented_cli_override_fields()


def loader_env_vars_by_field() -> dict[str, str]:
    """Return loader env var mapping independent from metadata helpers."""
    env_vars: dict[str, str] = {}
    for env_group in (
        loader.BOOL_ENVS,
        loader.COVERAGE_ENVS,
        loader.FLOAT_ENVS,
        loader.NON_NEGATIVE_INT_ENVS,
        loader.STRING_ENVS,
        loader.THRESHOLD_ENVS,
        loader.TUPLE_ENVS,
    ):
        for field_name, env_var in env_group:
            assert field_name not in env_vars
            env_vars[field_name] = env_var
    return env_vars


def implemented_cli_override_fields() -> set[str]:
    """Extract field names overridden by `apply_cli_overrides`."""
    syntax_tree = ast.parse(ARGS_MODULE.read_text(encoding="utf-8"))
    override_fields = {"mode"}
    for node in ast.walk(syntax_tree):
        if isinstance(node, ast.FunctionDef) and node.name == "apply_cli_overrides":
            override_fields.update(dict_literal_keys(node))
    return override_fields


def dict_literal_keys(node: ast.AST) -> set[str]:
    """Return string keys from dictionaries nested under AST node."""
    keys: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Dict):
            keys.update(
                key.value
                for key in child.keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            )
    return keys
