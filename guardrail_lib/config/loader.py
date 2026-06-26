"""Load guardrail configuration from pyproject and environment variables."""

from __future__ import annotations

import os
import shlex
import tomllib
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

from guardrail_lib.config import coercion, modes, schema

TUPLE_ENVS = (
    ("source_roots", "GUARDRAILS_SOURCE_ROOTS"),
    ("test_roots", "GUARDRAILS_TEST_ROOTS"),
    ("package_paths", "GUARDRAILS_PACKAGE_PATHS"),
    ("coverage_source", "GUARDRAILS_COVERAGE_SOURCE"),
    ("file_length_paths", "GUARDRAILS_FILE_LENGTH_PATHS"),
    ("structure_paths", "GUARDRAILS_STRUCTURE_PATHS"),
    ("structure_ignore_paths", "GUARDRAILS_STRUCTURE_IGNORE_PATHS"),
    ("structure_hint_patterns", "GUARDRAILS_STRUCTURE_HINT_PATTERNS"),
    ("vulture_paths", "GUARDRAILS_VULTURE_PATHS"),
    ("mutmut_args", "GUARDRAILS_MUTMUT_ARGS"),
    ("semgrep_args", "GUARDRAILS_SEMGREP_ARGS"),
    ("semgrep_profiles", "GUARDRAILS_SEMGREP_PROFILES"),
    ("secret_scan_profiles", "GUARDRAILS_SECRET_SCAN_PROFILES"),
    ("secret_scan_history_profiles", "GUARDRAILS_SECRET_SCAN_HISTORY_PROFILES"),
    ("markdownlint_paths", "GUARDRAILS_MARKDOWNLINT_PATHS"),
    ("yamllint_paths", "GUARDRAILS_YAMLLINT_PATHS"),
    ("taplo_paths", "GUARDRAILS_TAPLO_PATHS"),
    ("check_jsonschema_args", "GUARDRAILS_CHECK_JSONSCHEMA_ARGS"),
    (
        "source_without_test_change_error_profiles",
        "GUARDRAILS_SOURCE_WITHOUT_TEST_CHANGE_ERROR_PROFILES",
    ),
)
BOOL_ENVS = (
    ("require_tests", "GUARDRAILS_REQUIRE_TESTS"),
    ("enable_pip_audit", "GUARDRAILS_ENABLE_PIP_AUDIT"),
    ("enable_mutmut", "GUARDRAILS_ENABLE_MUTMUT"),
    ("enable_semgrep", "GUARDRAILS_ENABLE_SEMGREP"),
    ("enable_secret_scanning", "GUARDRAILS_ENABLE_SECRET_SCANNING"),
    ("enable_wemake", "GUARDRAILS_ENABLE_WEMAKE"),
    ("enable_interrogate", "GUARDRAILS_ENABLE_INTERROGATE"),
    ("enable_markdownlint", "GUARDRAILS_ENABLE_MARKDOWNLINT"),
    ("enable_yamllint", "GUARDRAILS_ENABLE_YAMLLINT"),
    ("enable_taplo", "GUARDRAILS_ENABLE_TAPLO"),
    ("enable_check_jsonschema", "GUARDRAILS_ENABLE_CHECK_JSONSCHEMA"),
    ("allow_source_without_test_change", "GUARDRAILS_ALLOW_SOURCE_WITHOUT_TEST_CHANGE"),
    ("diagnostic_artifacts_enabled", "GUARDRAILS_DIAGNOSTIC_ARTIFACTS_ENABLED"),
)
COVERAGE_ENVS = (
    ("coverage_fail_under", "GUARDRAILS_COVERAGE_FAIL_UNDER"),
    ("diff_cover_fail_under", "GUARDRAILS_DIFF_COVER_FAIL_UNDER"),
)
THRESHOLD_ENVS = (
    ("file_length_max_physical", "GUARDRAILS_FILE_LENGTH_MAX_PHYSICAL"),
    ("file_length_max_source", "GUARDRAILS_FILE_LENGTH_MAX_SOURCE"),
    ("change_warn_lines", "GUARDRAILS_CHANGE_WARN_LINES"),
    ("change_block_lines", "GUARDRAILS_CHANGE_BLOCK_LINES"),
    ("change_warn_files", "GUARDRAILS_CHANGE_WARN_FILES"),
    ("change_block_files", "GUARDRAILS_CHANGE_BLOCK_FILES"),
    ("suppression_max_new", "GUARDRAILS_SUPPRESSION_MAX_NEW"),
    ("folder_file_warn", "GUARDRAILS_FOLDER_FILE_WARN"),
    ("folder_file_block", "GUARDRAILS_FOLDER_FILE_BLOCK"),
    ("structure_cluster_min", "GUARDRAILS_STRUCTURE_CLUSTER_MIN"),
    ("interrogate_fail_under", "GUARDRAILS_INTERROGATE_FAIL_UNDER"),
)
STRING_ENVS = (
    ("file_length_baseline", "GUARDRAILS_FILE_LENGTH_BASELINE"),
    ("pyright_type_checking_mode", "GUARDRAILS_PYRIGHT_TYPE_CHECKING_MODE"),
    ("xenon_max_absolute", "GUARDRAILS_XENON_MAX_ABSOLUTE"),
    ("xenon_max_modules", "GUARDRAILS_XENON_MAX_MODULES"),
    ("xenon_max_average", "GUARDRAILS_XENON_MAX_AVERAGE"),
    ("diagnostic_artifacts_dir", "GUARDRAILS_DIAGNOSTIC_ARTIFACTS_DIR"),
    ("secret_scanner", "GUARDRAILS_SECRET_SCANNER"),
)


def read_pyproject(path: Path | None = None) -> dict[str, Any]:
    """Read `[tool.ai_guardrails]` from pyproject.toml."""

    path = path or Path("pyproject.toml")
    if not path.exists():
        return {}
    with path.open("rb") as handle:
        payload = tomllib.load(handle)
    tool = payload.get("tool", {})
    if not isinstance(tool, dict):
        return {}
    config = tool.get("ai_guardrails", {})
    if not isinstance(config, dict):
        return {}
    return config


def apply_pyproject(
    config: schema.GuardrailConfig,
    raw: dict[str, Any],
) -> schema.GuardrailConfig:
    """Apply raw pyproject settings after resolving any mode preset."""

    mode_value = raw.get("mode")
    if mode_value is not None:
        mode = coercion.as_choice(mode_value, "mode", schema.VALID_MODES)
        config = modes.apply_mode(config, mode)
    return replace(config, **coercion.coerce_updates(raw))


def env_value(
    env_name: str,
    parser: Callable[[object, str], object],
) -> object | None:
    """Return a parsed environment value when present."""

    if env_name not in os.environ:
        return None
    return parser(os.environ[env_name], env_name)


def merge_env_values(
    updates: dict[str, object],
    envs: tuple[tuple[str, str], ...],
    parser: Callable[[object, str], object],
) -> None:
    """Merge environment overrides of a common value type."""

    for field_name, env_name in envs:
        parsed_value = env_value(env_name, parser)
        if parsed_value is not None:
            updates[field_name] = parsed_value


def apply_env(config: schema.GuardrailConfig) -> schema.GuardrailConfig:
    """Apply GUARDRAILS_* environment overrides."""

    mode = os.getenv("GUARDRAILS_MODE")
    if mode is not None:
        selected = coercion.as_choice(mode, "GUARDRAILS_MODE", schema.VALID_MODES)
        config = modes.apply_mode(config, selected)

    updates: dict[str, object] = {}
    merge_env_values(updates, TUPLE_ENVS, coercion.as_tuple)
    merge_env_values(updates, BOOL_ENVS, coercion.as_bool)
    merge_env_values(updates, COVERAGE_ENVS, coercion.as_int)
    merge_env_values(updates, THRESHOLD_ENVS, coercion.as_int)
    merge_env_values(updates, STRING_ENVS, coercion.as_str)
    apply_special_envs(updates)
    return replace(config, **updates)


def apply_special_envs(updates: dict[str, object]) -> None:
    """Apply env overrides that need shell parsing or choice validation."""

    pip_audit_args = os.getenv("GUARDRAILS_PIP_AUDIT_ARGS")
    if pip_audit_args is not None:
        updates["pip_audit_args"] = tuple(shlex.split(pip_audit_args))
    architecture_tool = os.getenv("GUARDRAILS_ARCHITECTURE_TOOL")
    if architecture_tool is not None:
        updates["architecture_tool"] = coercion.as_choice(
            architecture_tool,
            "GUARDRAILS_ARCHITECTURE_TOOL",
            schema.VALID_ARCHITECTURE_TOOLS,
        )


def load_config() -> schema.GuardrailConfig:
    """Load guardrail configuration from pyproject and environment overrides."""

    config = schema.GuardrailConfig()
    config = apply_pyproject(config, read_pyproject())
    return apply_env(config)
