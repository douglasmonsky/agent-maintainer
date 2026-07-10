"""Regression matrix for the authoritative configuration contract."""

from __future__ import annotations

import math
import shlex
from collections.abc import Callable
from dataclasses import fields, replace
from pathlib import Path

import pytest

from agent_maintainer.config import coercion, loader, registry, schema, validation
from agent_maintainer.core import args as core_args

EXPECTED_CONFIG_FIELD_COUNT = 130


def assert_issue(
    issue: validation.ConfigIssue,
    *,
    source: str,
    key: str,
    message: str = "",
) -> None:
    """Assert stable source-aware diagnostic fields."""

    assert issue.source == source
    assert issue.key == key
    if message:
        assert issue.message == message


def capture_config_error(
    action: Callable[..., object],
    *args: object,
    **kwargs: object,
) -> validation.ConfigValidationError:
    """Run one action and return its expected configuration failure."""

    expected = pytest.raises(validation.ConfigValidationError)
    with expected:
        action(*args, **kwargs)
    assert expected.excinfo is not None
    return expected.excinfo.value


def test_registry_covers_config_fields() -> None:
    """The registry and resolved dataclass cannot drift independently."""

    field_names = {field.name for field in fields(schema.MaintainerConfig)}

    assert len(field_names) == EXPECTED_CONFIG_FIELD_COUNT
    assert set(registry.FIELD_SPECS) == field_names
    assert len({spec.toml_key for spec in registry.FIELD_SPECS.values()}) == len(field_names)


def test_environment_defaults_round_trip() -> None:
    """Every declared environment capability parses its resolved default."""

    expected = schema.MaintainerConfig()
    environment = {
        spec.env_var: _environment_text(spec, getattr(expected, spec.field_name))
        for spec in registry.env_specs()
    }

    assert loader.apply_env(expected, environment=environment) == expected


def test_loader_compatibility_helpers(tmp_path: Path) -> None:
    """Established loader helpers retain their provider-neutral behavior."""

    (tmp_path / "agent-maintainer.toml").write_text('source_roots = ["lib"]\n', encoding="utf-8")
    updates: dict[str, object] = {}
    loader.merge_env_values(
        updates,
        (("change_warn_lines", "EXAMPLE_WARN_LINES"),),
        coercion.as_int,
        environment={"EXAMPLE_WARN_LINES": "42"},
    )

    assert loader.read_config(tmp_path) == {"source_roots": ["lib"]}
    assert updates == {"change_warn_lines": 42}


def test_compression_constants_are_public() -> None:
    """Named backend constants remain members of the registered choice set."""

    assert schema.NONE_COMPRESSION_BACKEND in schema.VALID_CONTEXT_COMPRESSION_BACKENDS
    assert schema.TRUNCATE_COMPRESSION_BACKEND in schema.VALID_CONTEXT_COMPRESSION_BACKENDS


def _environment_text(spec: registry.ConfigFieldSpec, value: object) -> str:
    if isinstance(value, tuple):
        return shlex.join(value) if spec.env_style == "shell" else ",".join(value)
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


@pytest.mark.parametrize(
    ("raw", "expected_key"),
    (
        ({"coverage_fail_nder": 90}, "tool.agent_maintainer.coverage_fail_nder"),
        ({"diagnostics": {"lod_dir": "logs"}}, "tool.agent_maintainer.diagnostics.lod_dir"),
        (
            {"workspaces": {"api": {"source_root": ["src"]}}},
            "tool.agent_maintainer.workspaces.api.source_root",
        ),
        ({"file_baselines": {"enabledd": True}}, "tool.agent_maintainer.file_baselines.enabledd"),
        (
            {"file_baselines": {"groups": {"docs": {"include": ["docs/**"], "rol": "docs"}}}},
            "tool.agent_maintainer.file_baselines.groups.docs.rol",
        ),
    ),
)
def test_unknown_keys_fail_at_every_nesting(
    raw: dict[str, object],
    expected_key: str,
) -> None:
    """Typos cannot silently disappear at any supported table depth."""

    error = capture_config_error(
        loader.apply_pyproject,
        schema.MaintainerConfig(),
        raw,
        source="settings.toml",
    )

    assert_issue(
        error.issues[0],
        source="settings.toml",
        key=expected_key,
        message="unknown configuration key",
    )


def test_neutral_error_has_source_and_prefix(tmp_path: Path) -> None:
    """Neutral-file diagnostics name the physical source and public key path."""

    config_path = tmp_path / "agent-maintainer.toml"
    config_path.write_text("coverage_fail_nder = 90\n", encoding="utf-8")

    error = capture_config_error(loader.load_config, tmp_path)

    assert_issue(
        error.issues[0],
        source=str(config_path),
        key="agent_maintainer.coverage_fail_nder",
    )


def test_nested_field_aliases_remain_compatible() -> None:
    """Established top-level spellings still feed canonical nested fields."""

    loaded = loader.apply_pyproject(
        schema.MaintainerConfig(),
        {
            "diagnostic_artifacts_enabled": False,
            "file_baselines_enabled": True,
        },
    )

    assert loaded.diagnostic_artifacts_enabled is False
    assert loaded.file_baselines_enabled is True


def test_alias_and_canonical_key_conflict_fails() -> None:
    """Two spellings for one field cannot create order-dependent policy."""

    raw = {
        "diagnostic_artifacts_enabled": False,
        "diagnostics": {"enabled": True},
    }
    with pytest.raises(validation.ConfigValidationError, match="cannot be combined"):
        loader.apply_pyproject(schema.MaintainerConfig(), raw)


def test_unknown_environment_name_fails_closed() -> None:
    """A misspelled public environment override cannot be ignored."""

    name = "AGENT_MAINTAINER_COVERAGE_FAIL_UNDR"
    error = capture_config_error(
        loader.apply_env,
        schema.MaintainerConfig(),
        environment={name: "90"},
    )

    assert_issue(error.issues[0], source="environment", key=name)


def test_malformed_shell_environment_fails_closed() -> None:
    """Shell-style overrides report their source instead of leaking ValueError."""

    name = "AGENT_MAINTAINER_PIP_AUDIT_ARGS"
    error = capture_config_error(
        loader.apply_env,
        schema.MaintainerConfig(),
        environment={name: "'unterminated"},
    )

    assert_issue(
        error.issues[0],
        source="environment",
        key=name,
        message="invalid shell syntax: No closing quotation",
    )


def test_runtime_env_is_not_treated_as_config() -> None:
    """Documented process controls coexist with fail-closed config names."""

    environment = {"AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT": "1"}

    assert loader.apply_env(schema.MaintainerConfig(), environment=environment) == (
        schema.MaintainerConfig()
    )


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    (
        ("coverage_fail_under", -1, "must be at least 0"),
        ("coverage_fail_under", 101, "must be at most 100"),
        ("file_length_max_physical", 0, "must be at least 1"),
        ("change_warn_lines", -1, "must be at least 0"),
        ("context_compression_target_ratio", 0, "must be greater than 0"),
        ("context_compression_target_ratio", 1.1, "must be at most 1"),
        ("context_compression_target_ratio", math.inf, "must be a finite number"),
    ),
)
def test_numeric_bounds_are_enforced(
    field_name: str,
    value: object,
    message: str,
) -> None:
    """Registered minimum, maximum, and finite-number rules fail closed."""

    with pytest.raises(validation.ConfigValidationError, match=message):
        loader.apply_pyproject(schema.MaintainerConfig(), {field_name: value})


def test_bool_is_not_an_integer() -> None:
    """Python's bool-as-int relationship never leaks into the config API."""

    with pytest.raises(validation.ConfigValidationError, match="must be an integer"):
        loader.apply_pyproject(schema.MaintainerConfig(), {"coverage_fail_under": True})

    invalid = replace(schema.MaintainerConfig(), coverage_fail_under=True)
    with pytest.raises(validation.ConfigValidationError, match="booleans are not integers"):
        validation.validate_config(invalid)


@pytest.mark.parametrize(
    ("raw", "expected_key"),
    (
        ({"change_warn_lines": 900}, "change_block_lines"),
        ({"change_warn_files": 30}, "change_block_files"),
        ({"folder_file_warn": 50}, "folder_file_block"),
        ({"file_length_max_source": 700}, "file_length_max_physical"),
        ({"context_compression_require_backend": True}, "context_compression_require_backend"),
        (
            {"context_compression_enabled": True, "context_compression_backend": "none"},
            "context_compression_backend",
        ),
    ),
)
def test_cross_field_contradictions_are_rejected(
    raw: dict[str, object],
    expected_key: str,
) -> None:
    """The merged policy cannot contain contradictory thresholds or modes."""

    with pytest.raises(validation.ConfigValidationError) as caught:
        loader.apply_pyproject(schema.MaintainerConfig(), raw)

    assert expected_key in {issue.key for issue in caught.value.issues}


@pytest.mark.parametrize(
    ("raw", "expected_key"),
    (
        ({"source_roots": ["/tmp/src"]}, "source_roots"),
        ({"test_roots": ["../tests"]}, "test_roots"),
        ({"file_length_baseline": "~/baseline.json"}, "file_length_baseline"),
        ({"ratchet_baseline_path": r"C:\temp\baseline.json"}, "ratchet_baseline_path"),
        ({"workspaces": {"api": {"source_roots": ["../api"]}}}, "workspaces.api.source_roots"),
        (
            {"file_baselines": {"groups": {"docs": {"include": ["../docs/**"]}}}},
            "file_baselines.groups.docs.include",
        ),
    ),
)
def test_paths_must_be_repository_relative(
    raw: dict[str, object],
    expected_key: str,
) -> None:
    """Global and nested filesystem inputs stay inside the repository."""

    with pytest.raises(validation.ConfigValidationError) as caught:
        loader.apply_pyproject(schema.MaintainerConfig(), raw)

    assert expected_key in {issue.key for issue in caught.value.issues}


def test_profiles_are_registry_validated() -> None:
    """Profile-bearing fields cannot silently target a nonexistent run."""

    with pytest.raises(validation.ConfigValidationError, match="unknown verification profile"):
        loader.apply_pyproject(
            schema.MaintainerConfig(),
            {"semgrep_profiles": ["security", "never-heard-of-it"]},
        )


def test_file_environment_and_cli_precedence(tmp_path: Path) -> None:
    """Valid overrides resolve deterministically from file to env to CLI."""

    (tmp_path / "agent-maintainer.toml").write_text(
        'source_roots = ["file-src"]\n',
        encoding="utf-8",
    )
    loaded = loader.load_config(tmp_path)
    loaded = loader.apply_env(
        loaded,
        environment={"AGENT_MAINTAINER_SOURCE_ROOTS": "env-src"},
    )
    parsed = core_args.parse_args(["--source-root", "cli-src"])

    assert core_args.apply_cli_overrides(loaded, parsed).source_roots == ("cli-src",)
