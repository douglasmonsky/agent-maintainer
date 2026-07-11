"""Tests low-level Agent Maintainer config coercion contracts."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from agent_maintainer.config import coercion, registry, schema, validation


def capture_validation_error(
    action: Callable[[], object],
) -> validation.ConfigValidationError:
    """Return the structured validation error raised by one coercion action."""

    with pytest.raises(validation.ConfigValidationError) as caught:
        action()
    return caught.value


def test_compression_constants_are_public() -> None:
    """Named backend constants remain members of the registered choice set."""

    assert schema.NONE_COMPRESSION_BACKEND in schema.VALID_CONTEXT_COMPRESSION_BACKENDS
    assert schema.TRUNCATE_COMPRESSION_BACKEND in schema.VALID_CONTEXT_COMPRESSION_BACKENDS


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


@pytest.mark.parametrize("non_finite", (float("inf"), "inf"))
def test_as_float_preserves_numeric_values_and_error_context(non_finite: object) -> None:
    """Float coercion retains values and names non-finite input precisely."""

    assert coercion.as_float(1, "ratio") == 1.0
    with pytest.raises(TypeError, match=r"^ratio must be a finite number$"):
        coercion.as_float(non_finite, "ratio")


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


@pytest.mark.parametrize(
    ("action", "expected_key"),
    (
        (
            lambda: coercion.coerce_file_baseline_group(
                "docs",
                {"include": ["docs/**"], "typo": True},
                source="settings.toml",
            ),
            "tool.agent_maintainer.file_baselines.groups.docs.typo",
        ),
        (
            lambda: coercion.coerce_file_baselines(
                {"typo": True},
                source="settings.toml",
            ),
            "tool.agent_maintainer.file_baselines.typo",
        ),
        (
            lambda: coercion.coerce_workspace(
                "api",
                {"typo": True},
                source="settings.toml",
            ),
            "tool.agent_maintainer.workspaces.api.typo",
        ),
        (
            lambda: coercion.coerce_workspaces(
                {"api": {"typo": True}},
                source="settings.toml",
            ),
            "tool.agent_maintainer.workspaces.api.typo",
        ),
        (
            lambda: coercion.coerce_diagnostics(
                {"typo": True},
                source="settings.toml",
            ),
            "tool.agent_maintainer.diagnostics.typo",
        ),
        (
            lambda: coercion.coerce_field_value(
                registry.FIELD_SPECS["pyright_strict_baseline"],
                "../outside.json",
                "pyright_strict_baseline",
                source="settings.toml",
            ),
            "pyright_strict_baseline",
        ),
    ),
)
def test_coercion_validation_preserves_custom_source(
    action: Callable[[], object],
    expected_key: str,
) -> None:
    """Each public coercion boundary forwards its diagnostic source."""

    error = capture_validation_error(action)

    assert [(issue.source, issue.key) for issue in error.issues] == [
        ("settings.toml", expected_key),
    ]


def test_coerce_updates_preserves_custom_source_and_prefix() -> None:
    """Top-level coercion forwards both diagnostic location components."""

    error = capture_validation_error(
        lambda: coercion.coerce_updates(
            {"typo": True},
            source="settings.toml",
            prefix="agent_maintainer",
        )
    )

    assert [(issue.source, issue.key) for issue in error.issues] == [
        ("settings.toml", "agent_maintainer.typo"),
    ]


def test_coerce_field_value_only_allows_empty_strings_when_registered() -> None:
    """The allow-empty flag cannot weaken every registered string field."""

    allow_empty = registry.FIELD_SPECS["file_length_baseline"]
    require_value = registry.FIELD_SPECS["pyright_strict_baseline"]

    assert coercion.coerce_field_value(allow_empty, "", "file_length_baseline") == ""
    with pytest.raises(TypeError, match="pyright_strict_baseline must be a non-empty string"):
        coercion.coerce_field_value(require_value, "", "pyright_strict_baseline")


def test_named_nested_tables_report_exact_type_errors() -> None:
    """Nested table errors keep stable public names for remediation."""

    with pytest.raises(TypeError, match=r"^file_baselines\.groups name must not be empty$"):
        coercion.coerce_file_baseline_group(" ", {"include": ["docs/**"]})
    with pytest.raises(TypeError, match=r"^file_baselines\.groups\.docs must be a table$"):
        coercion.coerce_file_baseline_group("docs", [])
    with pytest.raises(TypeError, match=r"^diagnostics must be a table$"):
        coercion.coerce_diagnostics([])


def test_nested_coercers_forward_custom_source(monkeypatch: pytest.MonkeyPatch) -> None:
    """Nested table coercers retain the caller's diagnostic source."""

    observed: list[tuple[str, str]] = []

    def fake_group(
        name: str,
        raw_value: object,
        *,
        source: str = coercion.DEFAULT_CONFIG_SOURCE,
    ) -> schema.FileBaselineGroupConfig:
        del raw_value
        observed.append(("group", source))
        return schema.FileBaselineGroupConfig(name=name, include=("docs/**",))

    def fake_workspace(
        name: str,
        raw_value: object,
        *,
        source: str = coercion.DEFAULT_CONFIG_SOURCE,
    ) -> schema.WorkspaceConfig:
        del raw_value
        observed.append(("workspace", source))
        return schema.WorkspaceConfig(name=name)

    def fake_field(
        spec: registry.ConfigFieldSpec,
        value: object,
        field_name: str,
        *,
        source: str = coercion.DEFAULT_CONFIG_SOURCE,
    ) -> object:
        del spec, field_name
        observed.append(("field", source))
        return value

    monkeypatch.setattr(coercion, "coerce_file_baseline_group", fake_group)
    monkeypatch.setattr(coercion, "coerce_workspace", fake_workspace)
    monkeypatch.setattr(coercion, "coerce_field_value", fake_field)

    coercion.coerce_file_baselines(
        {"groups": {"docs": {"include": ["docs/**"]}}},
        source="settings.toml",
    )
    coercion.coerce_workspaces({"api": {}}, source="settings.toml")
    coercion.coerce_diagnostics({"enabled": True}, source="settings.toml")

    assert observed == [
        ("group", "settings.toml"),
        ("workspace", "settings.toml"),
        ("field", "settings.toml"),
    ]


def test_coerce_updates_forwards_source_to_nested_coercers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The aggregate update boundary retains source across every branch."""

    observed: list[tuple[str, str]] = []

    def fake_field(
        spec: registry.ConfigFieldSpec,
        value: object,
        field_name: str,
        *,
        source: str = coercion.DEFAULT_CONFIG_SOURCE,
    ) -> object:
        del spec, field_name
        observed.append(("field", source))
        return value

    def fake_workspaces(
        raw_value: object,
        *,
        source: str = coercion.DEFAULT_CONFIG_SOURCE,
    ) -> tuple[schema.WorkspaceConfig, ...]:
        del raw_value
        observed.append(("workspaces", source))
        return ()

    def fake_diagnostics(
        raw_value: object,
        *,
        source: str = coercion.DEFAULT_CONFIG_SOURCE,
    ) -> dict[str, object]:
        del raw_value
        observed.append(("diagnostics", source))
        return {}

    def fake_file_baselines(
        raw_value: object,
        *,
        source: str = coercion.DEFAULT_CONFIG_SOURCE,
    ) -> dict[str, object]:
        del raw_value
        observed.append(("file_baselines", source))
        return {}

    monkeypatch.setattr(coercion, "coerce_field_value", fake_field)
    monkeypatch.setattr(coercion, "coerce_workspaces", fake_workspaces)
    monkeypatch.setattr(coercion, "coerce_diagnostics", fake_diagnostics)
    monkeypatch.setattr(coercion, "coerce_file_baselines", fake_file_baselines)

    coercion.coerce_updates(
        {
            "coverage_fail_under": 90,
            "workspaces": {"api": {}},
            "diagnostics": {"enabled": True},
            "file_baselines": {"groups": {"docs": {"include": ["docs/**"]}}},
        },
        source="settings.toml",
    )

    assert observed == [
        ("field", "settings.toml"),
        ("workspaces", "settings.toml"),
        ("diagnostics", "settings.toml"),
        ("file_baselines", "settings.toml"),
    ]


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
