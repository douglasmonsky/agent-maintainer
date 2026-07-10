"""Authoritative public configuration field and nested-table registry."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from agent_maintainer.config import registry_capabilities, schema_fields

ValueKind = Literal[
    "bool",
    "choice",
    "float",
    "int",
    "non-negative-int",
    "str",
    "tuple",
    "workspaces",
    "file-baseline-groups",
]

CLI_OVERRIDE_NONE = "none"
CLI_OVERRIDE_VERIFY = "verify"
STABILITY_BETA = "beta"
STABILITY_STABLE = "stable"

TUPLE_FIELDS = schema_fields.TUPLE_FIELDS
BOOL_FIELDS = schema_fields.BOOL_FIELDS
NON_NEGATIVE_INT_FIELDS = schema_fields.NON_NEGATIVE_INT_FIELDS
INT_FIELDS = schema_fields.INT_FIELDS
FLOAT_FIELDS = schema_fields.FLOAT_FIELDS
STR_FIELDS = schema_fields.STR_FIELDS

VALID_MODES = frozenset(("custom", "legacy-ratchet", "fresh-strict"))
VALID_ARCHITECTURE_TOOLS = frozenset(("import-linter", "tach"))
VALID_CONTEXT_COMPRESSION_BACKENDS = frozenset(("none", "truncate", "extractive", "headroom"))
VALID_FILE_BASELINE_MODES = frozenset(("advisory", "blocking"))
VALID_PYRIGHT_MODES = frozenset(("off", "basic", "standard", "strict"))
VALID_XENON_RANKS = frozenset(("A", "B", "C", "D", "E", "F"))
VALID_RUNTIME_EVENT_LEVELS = frozenset(("debug", "info", "warning", "error"))
SUPPORTED_SECRET_SCANNERS = frozenset(("gitleaks",))

CHOICE_FIELDS = MappingProxyType(
    {
        "mode": VALID_MODES,
        "architecture_tool": VALID_ARCHITECTURE_TOOLS,
        "context_compression_backend": VALID_CONTEXT_COMPRESSION_BACKENDS,
        "file_baselines_mode": VALID_FILE_BASELINE_MODES,
        "pyright_type_checking_mode": VALID_PYRIGHT_MODES,
        "runtime_event_level": VALID_RUNTIME_EVENT_LEVELS,
        "secret_scanner": SUPPORTED_SECRET_SCANNERS,
        "xenon_max_absolute": VALID_XENON_RANKS,
        "xenon_max_modules": VALID_XENON_RANKS,
        "xenon_max_average": VALID_XENON_RANKS,
    }
)
NESTED_FIELD_KINDS: Mapping[str, ValueKind] = MappingProxyType(
    {
        "workspaces": "workspaces",
        "file_baselines": "file-baseline-groups",
    }
)
NESTED_TOML_KEYS = MappingProxyType(
    {
        "diagnostic_artifacts_enabled": "diagnostics.enabled",
        "diagnostic_artifacts_dir": "diagnostics.log_dir",
        "diagnostic_run_history_limit": "diagnostics.run_history_limit",
        "file_baselines_enabled": "file_baselines.enabled",
        "file_baselines_mode": "file_baselines.mode",
        "file_baselines": "file_baselines.groups",
    }
)
LEGACY_TOML_ALIASES = MappingProxyType(
    {
        field_name: (field_name,)
        for field_name in (
            "diagnostic_artifacts_enabled",
            "diagnostic_artifacts_dir",
            "diagnostic_run_history_limit",
            "file_baselines_enabled",
            "file_baselines_mode",
        )
    }
)

DIAGNOSTIC_FIELD_MAP = MappingProxyType(
    {
        "enabled": "diagnostic_artifacts_enabled",
        "log_dir": "diagnostic_artifacts_dir",
        "run_history_limit": "diagnostic_run_history_limit",
    }
)
DIAGNOSTIC_KEYS = frozenset(DIAGNOSTIC_FIELD_MAP)
WORKSPACE_KEYS = frozenset(
    (
        "source_roots",
        "test_roots",
        "package_paths",
        "coverage_source",
        "typescript_lint_command",
        "typescript_typecheck_command",
        "typescript_test_command",
    )
)
WORKSPACE_PATH_KEYS = frozenset(("source_roots", "test_roots", "package_paths", "coverage_source"))
FILE_BASELINE_KEYS = frozenset(("enabled", "mode", "groups"))
FILE_BASELINE_GROUP_KEYS = frozenset(
    (
        "include",
        "exclude",
        "role",
        "max_physical_lines",
        "max_nonblank_lines",
        "changed_file_warn",
        "changed_line_warn",
    )
)

PERCENT_FIELDS = frozenset(
    ("coverage_fail_under", "diff_cover_fail_under", "interrogate_fail_under", "mutmut_min_score")
)
POSITIVE_INT_FIELDS = frozenset(
    (
        "file_length_max_physical",
        "file_length_max_source",
        "ruff_max_complexity",
        "structure_cluster_min",
        "context_default_budget_chars",
        "context_hook_budget_chars",
        "context_last_failure_budget_chars",
        "context_pack_budget_chars",
        "context_large_file_threshold_lines",
        "context_large_file_threshold_bytes",
        "context_max_direct_file_read_lines",
        "context_max_direct_log_read_lines",
        "context_max_failure_items",
        "context_max_paths_default",
        "large_change_max_active_plans",
    )
)
PATH_FIELDS = frozenset(
    (
        "source_roots",
        "test_roots",
        "package_paths",
        "coverage_source",
        "file_length_paths",
        "vulture_paths",
        "structure_paths",
        "structure_ignore_paths",
        "cohesive_change_override_paths",
        "large_change_plan_dirs",
        "markdownlint_paths",
        "yamllint_paths",
        "taplo_paths",
        "file_length_baseline",
        "pyright_strict_baseline",
        "ratchet_baseline_path",
        "ratchet_guidance_path",
    )
)
PROFILE_FIELDS = frozenset(
    field
    for field in TUPLE_FIELDS
    if field.endswith("_profiles") or field.endswith("_error_profiles")
)

CLI_OVERRIDE_FIELDS = registry_capabilities.CLI_OVERRIDE_FIELDS
STABLE_FIELDS = registry_capabilities.STABLE_FIELDS

SHELL_ENV_FIELDS = frozenset(("pip_audit_args", "osv_scanner_args", "trivy_args"))
TUPLE_ENV_FIELDS = TUPLE_FIELDS - SHELL_ENV_FIELDS
BOOL_ENV_FIELDS = BOOL_FIELDS - frozenset(("file_baselines_enabled",))
INT_ENV_FIELDS = frozenset(
    (
        "coverage_fail_under",
        "diff_cover_fail_under",
        "file_length_max_physical",
        "file_length_max_source",
        "change_warn_lines",
        "change_block_lines",
        "change_warn_files",
        "change_block_files",
        "suppression_max_new",
        "folder_file_warn",
        "folder_file_block",
        "structure_cluster_min",
        "cohesive_change_override_max_lines",
        "cohesive_change_override_max_files",
        "interrogate_fail_under",
    )
)
STRING_ENV_FIELDS = STR_FIELDS
SPECIAL_ENV_FIELDS = frozenset(("mode", "architecture_tool", "context_compression_backend"))
ENV_FIELDS = frozenset(
    TUPLE_ENV_FIELDS
    | BOOL_ENV_FIELDS
    | NON_NEGATIVE_INT_FIELDS
    | FLOAT_FIELDS
    | INT_ENV_FIELDS
    | STRING_ENV_FIELDS
    | SHELL_ENV_FIELDS
    | SPECIAL_ENV_FIELDS
)
NON_CONFIG_ENV_VARS = frozenset(
    (
        "AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT",
        "AGENT_MAINTAINER_BACKGROUND_PR_WAIT",
        "AGENT_MAINTAINER_BACKGROUND_WAIT",
        "AGENT_MAINTAINER_CODEX_APP_SERVER_TIMEOUT_SECONDS",
        "AGENT_MAINTAINER_CODEX_BIN",
        "AGENT_MAINTAINER_CODEX_REWAKE",
        "AGENT_MAINTAINER_CODEX_THREAD_ID",
        "AGENT_MAINTAINER_COHESIVE_CHANGE_OVERRIDE_REQUESTED",
        "AGENT_MAINTAINER_KEEP_MUTANTS",
        "AGENT_MAINTAINER_RUN_RELEASE_TESTS",
        "AGENT_MAINTAINER_WRITE_BYTECODE",
    )
)


@dataclass(frozen=True)
class ConfigFieldSpec:
    """One complete public configuration field contract."""

    field_name: str
    toml_key: str
    value_kind: ValueKind
    toml_aliases: tuple[str, ...] = ()
    env_var: str = ""
    env_style: str = "standard"
    choices: frozenset[str] = frozenset()
    minimum: float | None = None
    maximum: float | None = None
    minimum_exclusive: bool = False
    path_value: bool = False
    profile_values: bool = False
    allow_empty: bool = False
    cli_override: str = CLI_OVERRIDE_NONE
    docs_label: str = ""
    description: str = ""
    stability: str = STABILITY_BETA

    @property
    def has_env_override(self) -> bool:
        """Return whether the field has an environment override."""

        return bool(self.env_var)

    @property
    def has_cli_override(self) -> bool:
        """Return whether the verifier CLI can override the field."""

        return self.cli_override != CLI_OVERRIDE_NONE


FIELD_KINDS: Mapping[str, ValueKind] = MappingProxyType(
    {
        **{field_name: "tuple" for field_name in TUPLE_FIELDS},
        **{field_name: "bool" for field_name in BOOL_FIELDS},
        **{field_name: "non-negative-int" for field_name in NON_NEGATIVE_INT_FIELDS},
        **{field_name: "int" for field_name in INT_FIELDS},
        **{field_name: "float" for field_name in FLOAT_FIELDS},
        **{field_name: "str" for field_name in STR_FIELDS},
        **{field_name: "choice" for field_name in CHOICE_FIELDS},
        **NESTED_FIELD_KINDS,
    }
)
ZERO = float(0)
ONE = float(1)
HUNDRED = float(100)


def _value_kind(field_name: str) -> ValueKind:
    try:
        return FIELD_KINDS[field_name]
    except KeyError as exc:
        raise ValueError(f"unregistered config field: {field_name}") from exc


def _minimum(field_name: str) -> float | None:
    if field_name == "context_compression_target_ratio":
        return ZERO
    if field_name in PERCENT_FIELDS or field_name in POSITIVE_INT_FIELDS:
        return ONE if field_name in POSITIVE_INT_FIELDS else ZERO
    if field_name in NON_NEGATIVE_INT_FIELDS or field_name in INT_FIELDS:
        return ZERO
    return None


def _maximum(field_name: str) -> float | None:
    if field_name in PERCENT_FIELDS:
        return HUNDRED
    if field_name == "context_compression_target_ratio":
        return ONE
    return None


def _env_var(field_name: str) -> str:
    if field_name not in ENV_FIELDS:
        return ""
    return f"AGENT_MAINTAINER_{field_name.upper()}"


def _build_spec(field_name: str) -> ConfigFieldSpec:
    label = field_name.replace("_", " ").title()
    return ConfigFieldSpec(
        field_name=field_name,
        toml_key=NESTED_TOML_KEYS.get(field_name, field_name),
        value_kind=_value_kind(field_name),
        toml_aliases=LEGACY_TOML_ALIASES.get(field_name, ()),
        env_var=_env_var(field_name),
        env_style="shell" if field_name in SHELL_ENV_FIELDS else "standard",
        choices=CHOICE_FIELDS.get(field_name, frozenset()),
        minimum=_minimum(field_name),
        maximum=_maximum(field_name),
        minimum_exclusive=field_name == "context_compression_target_ratio",
        path_value=field_name in PATH_FIELDS,
        profile_values=field_name in PROFILE_FIELDS,
        allow_empty=field_name == "file_length_baseline",
        cli_override=(
            CLI_OVERRIDE_VERIFY if field_name in CLI_OVERRIDE_FIELDS else CLI_OVERRIDE_NONE
        ),
        docs_label=label,
        description=f"Configure {label.lower()}.",
        stability=STABILITY_STABLE if field_name in STABLE_FIELDS else STABILITY_BETA,
    )


DECLARED_FIELDS = frozenset(
    TUPLE_FIELDS
    | BOOL_FIELDS
    | NON_NEGATIVE_INT_FIELDS
    | INT_FIELDS
    | FLOAT_FIELDS
    | STR_FIELDS
    | frozenset(CHOICE_FIELDS)
    | frozenset(NESTED_FIELD_KINDS)
)
FIELD_SPECS = MappingProxyType(
    {field_name: _build_spec(field_name) for field_name in sorted(DECLARED_FIELDS)}
)


def top_level_toml_keys() -> frozenset[str]:
    """Return every supported top-level TOML key from registered paths."""

    canonical = frozenset(spec.toml_key.split(".", 1)[0] for spec in FIELD_SPECS.values())
    aliases = frozenset(alias for spec in FIELD_SPECS.values() for alias in spec.toml_aliases)
    return canonical | aliases


def env_specs() -> tuple[ConfigFieldSpec, ...]:
    """Return registered environment-backed fields in deterministic order."""

    return tuple(spec for spec in FIELD_SPECS.values() if spec.env_var)


def known_environment_names() -> frozenset[str]:
    """Return config and runtime environment names accepted by the product."""

    return frozenset(spec.env_var for spec in env_specs()) | NON_CONFIG_ENV_VARS
