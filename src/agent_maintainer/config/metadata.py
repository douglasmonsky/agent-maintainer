"""Metadata inventory for public maintainer configuration fields."""

from __future__ import annotations

from dataclasses import dataclass, fields

from agent_maintainer.config import loader, schema

CLI_OVERRIDE_NONE = "none"
CLI_OVERRIDE_VERIFY = "verify"
STABILITY_BETA = "beta"
STABILITY_STABLE = "stable"
VALID_CLI_OVERRIDE_STATUSES = frozenset((CLI_OVERRIDE_NONE, CLI_OVERRIDE_VERIFY))
VALID_STABILITY_LEVELS = frozenset((STABILITY_BETA, STABILITY_STABLE))

DIAGNOSTIC_TOML_KEYS = (
    ("diagnostic_artifacts_enabled", "diagnostics.enabled"),
    ("diagnostic_artifacts_dir", "diagnostics.log_dir"),
    ("diagnostic_run_history_limit", "diagnostics.run_history_limit"),
)

CLI_OVERRIDE_FIELDS = frozenset(
    (
        "allow_source_without_test_change",
        "architecture_tool",
        "check_jsonschema_args",
        "coverage_fail_under",
        "coverage_source",
        "diff_cover_fail_under",
        "enable_check_jsonschema",
        "enable_interrogate",
        "enable_markdownlint",
        "enable_mutmut",
        "enable_pip_audit",
        "enable_secret_scanning",
        "enable_semgrep",
        "enable_taplo",
        "enable_wemake",
        "enable_yamllint",
        "file_length_baseline",
        "file_length_paths",
        "interrogate_fail_under",
        "markdownlint_paths",
        "mode",
        "mutmut_args",
        "package_paths",
        "require_tests",
        "secret_scan_history_profiles",
        "secret_scan_profiles",
        "secret_scanner",
        "semgrep_args",
        "semgrep_profiles",
        "source_roots",
        "taplo_paths",
        "test_roots",
        "vulture_paths",
        "yamllint_paths",
    )
)

STABLE_FIELDS = frozenset(
    (
        "allow_source_without_test_change",
        "architecture_tool",
        "change_block_files",
        "change_block_lines",
        "change_warn_files",
        "change_warn_lines",
        "coverage_fail_under",
        "coverage_source",
        "diff_cover_fail_under",
        "file_length_baseline",
        "file_length_max_physical",
        "file_length_max_source",
        "file_length_paths",
        "mode",
        "package_paths",
        "pyright_type_checking_mode",
        "require_tests",
        "ruff_max_complexity",
        "source_roots",
        "source_without_test_change_error_profiles",
        "suppression_max_new",
        "test_roots",
        "vulture_paths",
        "xenon_max_absolute",
        "xenon_max_average",
        "xenon_max_modules",
    )
)

ENV_GROUPS = (
    loader.BOOL_ENVS,
    loader.COVERAGE_ENVS,
    loader.FLOAT_ENVS,
    loader.NON_NEGATIVE_INT_ENVS,
    loader.STRING_ENVS,
    loader.THRESHOLD_ENVS,
    loader.TUPLE_ENVS,
)


@dataclass(frozen=True)
class ConfigFieldMetadata:
    """One field in Agent Maintainer's public configuration surface."""

    field_name: str
    toml_key: str
    env_var: str
    cli_override: str
    docs_label: str
    stability: str

    @property
    def has_env_override(self) -> bool:
        """Return whether field has an environment override."""
        return bool(self.env_var)

    @property
    def has_cli_override(self) -> bool:
        """Return whether verifier CLI can override field."""
        return self.cli_override != CLI_OVERRIDE_NONE


def env_vars_by_field() -> dict[str, str]:
    """Return configured environment variable names keyed by config field."""
    env_vars: dict[str, str] = {}
    for env_group in ENV_GROUPS:
        for field_name, env_var in env_group:
            env_vars[field_name] = env_var
    return env_vars


def build_field_metadata() -> dict[str, ConfigFieldMetadata]:
    """Build metadata for every `MaintainerConfig` dataclass field."""
    env_vars = env_vars_by_field()
    return {
        config_field.name: ConfigFieldMetadata(
            field_name=config_field.name,
            toml_key=toml_key_for(config_field.name),
            env_var=env_vars.get(config_field.name, ""),
            cli_override=cli_override_for(config_field.name),
            docs_label=docs_label_for(config_field.name),
            stability=stability_for(config_field.name),
        )
        for config_field in fields(schema.MaintainerConfig)
    }


def toml_key_for(field_name: str) -> str:
    """Return TOML key path for a config field."""
    for diagnostic_field_name, toml_key in DIAGNOSTIC_TOML_KEYS:
        if field_name == diagnostic_field_name:
            return toml_key
    return field_name


def cli_override_for(field_name: str) -> str:
    """Return verifier CLI override status for a config field."""
    if field_name in CLI_OVERRIDE_FIELDS:
        return CLI_OVERRIDE_VERIFY
    return CLI_OVERRIDE_NONE


def docs_label_for(field_name: str) -> str:
    """Return compact human-readable label for docs and diagnostics."""
    return field_name.replace("_", " ").title()


def stability_for(field_name: str) -> str:
    """Return public stability level for a config field."""
    if field_name in STABLE_FIELDS:
        return STABILITY_STABLE
    return STABILITY_BETA


FIELD_METADATA = build_field_metadata()
