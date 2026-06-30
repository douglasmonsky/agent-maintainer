"""Load Agent Maintainer configuration from pyproject and environment variables."""

from __future__ import annotations

import os
import shlex
import tomllib
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

from agent_maintainer.config import coercion, modes, schema

TUPLE_ENVS = (
    ("source_roots", "AGENT_MAINTAINER_SOURCE_ROOTS"),
    ("test_roots", "AGENT_MAINTAINER_TEST_ROOTS"),
    ("package_paths", "AGENT_MAINTAINER_PACKAGE_PATHS"),
    ("coverage_source", "AGENT_MAINTAINER_COVERAGE_SOURCE"),
    ("file_length_paths", "AGENT_MAINTAINER_FILE_LENGTH_PATHS"),
    ("structure_paths", "AGENT_MAINTAINER_STRUCTURE_PATHS"),
    ("structure_ignore_paths", "AGENT_MAINTAINER_STRUCTURE_IGNORE_PATHS"),
    ("structure_hint_patterns", "AGENT_MAINTAINER_STRUCTURE_HINT_PATTERNS"),
    ("vulture_paths", "AGENT_MAINTAINER_VULTURE_PATHS"),
    ("mutmut_args", "AGENT_MAINTAINER_MUTMUT_ARGS"),
    ("semgrep_args", "AGENT_MAINTAINER_SEMGREP_ARGS"),
    ("semgrep_profiles", "AGENT_MAINTAINER_SEMGREP_PROFILES"),
    ("osv_scanner_args", "AGENT_MAINTAINER_OSV_SCANNER_ARGS"),
    ("osv_scanner_profiles", "AGENT_MAINTAINER_OSV_SCANNER_PROFILES"),
    ("trivy_args", "AGENT_MAINTAINER_TRIVY_ARGS"),
    ("trivy_profiles", "AGENT_MAINTAINER_TRIVY_PROFILES"),
    ("sbom_args", "AGENT_MAINTAINER_SBOM_ARGS"),
    ("sbom_profiles", "AGENT_MAINTAINER_SBOM_PROFILES"),
    ("license_check_args", "AGENT_MAINTAINER_LICENSE_CHECK_ARGS"),
    ("license_check_profiles", "AGENT_MAINTAINER_LICENSE_CHECK_PROFILES"),
    ("secret_scan_profiles", "AGENT_MAINTAINER_SECRET_SCAN_PROFILES"),
    ("secret_scan_history_profiles", "AGENT_MAINTAINER_SECRET_SCAN_HISTORY_PROFILES"),
    ("markdownlint_paths", "AGENT_MAINTAINER_MARKDOWNLINT_PATHS"),
    ("yamllint_paths", "AGENT_MAINTAINER_YAMLLINT_PATHS"),
    ("taplo_paths", "AGENT_MAINTAINER_TAPLO_PATHS"),
    ("check_jsonschema_args", "AGENT_MAINTAINER_CHECK_JSONSCHEMA_ARGS"),
    (
        "cohesive_change_override_paths",
        "AGENT_MAINTAINER_COHESIVE_CHANGE_OVERRIDE_PATHS",
    ),
    (
        "source_without_test_change_error_profiles",
        "AGENT_MAINTAINER_SOURCE_WITHOUT_TEST_CHANGE_ERROR_PROFILES",
    ),
    ("large_change_plan_dirs", "AGENT_MAINTAINER_LARGE_CHANGE_PLAN_DIRS"),
)
BOOL_ENVS = (
    ("require_tests", "AGENT_MAINTAINER_REQUIRE_TESTS"),
    ("enable_pip_audit", "AGENT_MAINTAINER_ENABLE_PIP_AUDIT"),
    ("enable_mutmut", "AGENT_MAINTAINER_ENABLE_MUTMUT"),
    ("mutmut_result_ratchet_enabled", "AGENT_MAINTAINER_MUTMUT_RESULT_RATCHET_ENABLED"),
    ("enable_semgrep", "AGENT_MAINTAINER_ENABLE_SEMGREP"),
    ("enable_osv_scanner", "AGENT_MAINTAINER_ENABLE_OSV_SCANNER"),
    ("enable_trivy", "AGENT_MAINTAINER_ENABLE_TRIVY"),
    ("enable_sbom", "AGENT_MAINTAINER_ENABLE_SBOM"),
    ("enable_license_check", "AGENT_MAINTAINER_ENABLE_LICENSE_CHECK"),
    ("enable_secret_scanning", "AGENT_MAINTAINER_ENABLE_SECRET_SCANNING"),
    ("enable_wemake", "AGENT_MAINTAINER_ENABLE_WEMAKE"),
    ("enable_interrogate", "AGENT_MAINTAINER_ENABLE_INTERROGATE"),
    ("enable_markdownlint", "AGENT_MAINTAINER_ENABLE_MARKDOWNLINT"),
    ("enable_yamllint", "AGENT_MAINTAINER_ENABLE_YAMLLINT"),
    ("enable_taplo", "AGENT_MAINTAINER_ENABLE_TAPLO"),
    ("enable_check_jsonschema", "AGENT_MAINTAINER_ENABLE_CHECK_JSONSCHEMA"),
    ("allow_source_without_test_change", "AGENT_MAINTAINER_ALLOW_SOURCE_WITHOUT_TEST_CHANGE"),
    (
        "cohesive_change_override_enabled",
        "AGENT_MAINTAINER_COHESIVE_CHANGE_OVERRIDE_ENABLED",
    ),
    ("diagnostic_artifacts_enabled", "AGENT_MAINTAINER_DIAGNOSTIC_ARTIFACTS_ENABLED"),
    ("context_write_context_packs", "AGENT_MAINTAINER_CONTEXT_WRITE_CONTEXT_PACKS"),
    ("context_packs_local_only", "AGENT_MAINTAINER_CONTEXT_PACKS_LOCAL_ONLY"),
    ("context_pack_contains_source", "AGENT_MAINTAINER_CONTEXT_PACK_CONTAINS_SOURCE"),
    (
        "context_require_outline_for_large_files",
        "AGENT_MAINTAINER_CONTEXT_REQUIRE_OUTLINE_FOR_LARGE_FILES",
    ),
    ("context_compression_enabled", "AGENT_MAINTAINER_CONTEXT_COMPRESSION_ENABLED"),
    (
        "context_compression_require_backend",
        "AGENT_MAINTAINER_CONTEXT_COMPRESSION_REQUIRE_BACKEND",
    ),
    ("ratchet_enabled", "AGENT_MAINTAINER_RATCHET_ENABLED"),
    ("large_changes_enabled", "AGENT_MAINTAINER_LARGE_CHANGES_ENABLED"),
    (
        "large_change_allow_expired_plans",
        "AGENT_MAINTAINER_LARGE_CHANGE_ALLOW_EXPIRED_PLANS",
    ),
    (
        "large_change_require_required_sections",
        "AGENT_MAINTAINER_LARGE_CHANGE_REQUIRE_REQUIRED_SECTIONS",
    ),
    (
        "large_change_fail_out_of_plan_paths",
        "AGENT_MAINTAINER_LARGE_CHANGE_FAIL_OUT_OF_PLAN_PATHS",
    ),
)
NON_NEGATIVE_INT_ENVS = tuple(
    (field_name, f"AGENT_MAINTAINER_{field_name.upper()}")
    for field_name in sorted(schema.NON_NEGATIVE_INT_FIELDS)
)
FLOAT_ENVS = tuple(
    (field_name, f"AGENT_MAINTAINER_{field_name.upper()}")
    for field_name in sorted(schema.FLOAT_FIELDS)
)

COVERAGE_ENVS = (
    ("coverage_fail_under", "AGENT_MAINTAINER_COVERAGE_FAIL_UNDER"),
    ("diff_cover_fail_under", "AGENT_MAINTAINER_DIFF_COVER_FAIL_UNDER"),
)
THRESHOLD_ENVS = (
    ("file_length_max_physical", "AGENT_MAINTAINER_FILE_LENGTH_MAX_PHYSICAL"),
    ("file_length_max_source", "AGENT_MAINTAINER_FILE_LENGTH_MAX_SOURCE"),
    ("change_warn_lines", "AGENT_MAINTAINER_CHANGE_WARN_LINES"),
    ("change_block_lines", "AGENT_MAINTAINER_CHANGE_BLOCK_LINES"),
    ("change_warn_files", "AGENT_MAINTAINER_CHANGE_WARN_FILES"),
    ("change_block_files", "AGENT_MAINTAINER_CHANGE_BLOCK_FILES"),
    ("suppression_max_new", "AGENT_MAINTAINER_SUPPRESSION_MAX_NEW"),
    ("folder_file_warn", "AGENT_MAINTAINER_FOLDER_FILE_WARN"),
    ("folder_file_block", "AGENT_MAINTAINER_FOLDER_FILE_BLOCK"),
    ("structure_cluster_min", "AGENT_MAINTAINER_STRUCTURE_CLUSTER_MIN"),
    (
        "cohesive_change_override_max_lines",
        "AGENT_MAINTAINER_COHESIVE_CHANGE_OVERRIDE_MAX_LINES",
    ),
    (
        "cohesive_change_override_max_files",
        "AGENT_MAINTAINER_COHESIVE_CHANGE_OVERRIDE_MAX_FILES",
    ),
    ("interrogate_fail_under", "AGENT_MAINTAINER_INTERROGATE_FAIL_UNDER"),
)
STRING_ENVS = (
    ("file_length_baseline", "AGENT_MAINTAINER_FILE_LENGTH_BASELINE"),
    ("pyright_type_checking_mode", "AGENT_MAINTAINER_PYRIGHT_TYPE_CHECKING_MODE"),
    ("xenon_max_absolute", "AGENT_MAINTAINER_XENON_MAX_ABSOLUTE"),
    ("xenon_max_modules", "AGENT_MAINTAINER_XENON_MAX_MODULES"),
    ("xenon_max_average", "AGENT_MAINTAINER_XENON_MAX_AVERAGE"),
    ("diagnostic_artifacts_dir", "AGENT_MAINTAINER_DIAGNOSTIC_ARTIFACTS_DIR"),
    ("secret_scanner", "AGENT_MAINTAINER_SECRET_SCANNER"),
    ("ratchet_baseline_path", "AGENT_MAINTAINER_RATCHET_BASELINE_PATH"),
    ("ratchet_guidance_path", "AGENT_MAINTAINER_RATCHET_GUIDANCE_PATH"),
)


def read_pyproject(path: Path | None = None) -> dict[str, Any]:
    """Read `[tool.agent_maintainer]` from pyproject.toml."""

    path = path or Path("pyproject.toml")
    if not path.exists():
        return {}
    with path.open("rb") as handle:
        payload = tomllib.load(handle)
    tool = payload.get("tool", {})
    if not isinstance(tool, dict):
        return {}
    config = tool.get("agent_maintainer", {})
    if not isinstance(config, dict):
        return {}
    return config


def apply_pyproject(
    config: schema.MaintainerConfig,
    raw: dict[str, Any],
) -> schema.MaintainerConfig:
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


def apply_env(config: schema.MaintainerConfig) -> schema.MaintainerConfig:
    """Apply AGENT_MAINTAINER_* environment overrides."""

    mode = os.getenv("AGENT_MAINTAINER_MODE")
    if mode is not None:
        selected = coercion.as_choice(mode, "AGENT_MAINTAINER_MODE", schema.VALID_MODES)
        config = modes.apply_mode(config, selected)

    updates: dict[str, object] = {}
    merge_env_values(updates, TUPLE_ENVS, coercion.as_tuple)
    merge_env_values(updates, BOOL_ENVS, coercion.as_bool)
    merge_env_values(updates, NON_NEGATIVE_INT_ENVS, coercion.as_non_negative_int)
    merge_env_values(updates, COVERAGE_ENVS, coercion.as_int)
    merge_env_values(updates, THRESHOLD_ENVS, coercion.as_int)
    merge_env_values(updates, FLOAT_ENVS, coercion.as_float)
    merge_env_values(updates, STRING_ENVS, coercion.as_str)
    apply_special_envs(updates)
    return replace(config, **updates)


def apply_special_envs(updates: dict[str, object]) -> None:
    """Apply env overrides that need shell parsing or choice validation."""

    pip_audit_args = os.getenv("AGENT_MAINTAINER_PIP_AUDIT_ARGS")
    if pip_audit_args is not None:
        updates["pip_audit_args"] = tuple(shlex.split(pip_audit_args))
    osv_scanner_args = os.getenv("AGENT_MAINTAINER_OSV_SCANNER_ARGS")
    if osv_scanner_args is not None:
        updates["osv_scanner_args"] = tuple(shlex.split(osv_scanner_args))
    trivy_args = os.getenv("AGENT_MAINTAINER_TRIVY_ARGS")
    if trivy_args is not None:
        updates["trivy_args"] = tuple(shlex.split(trivy_args))
    architecture_tool = os.getenv("AGENT_MAINTAINER_ARCHITECTURE_TOOL")
    if architecture_tool is not None:
        updates["architecture_tool"] = coercion.as_choice(
            architecture_tool,
            "AGENT_MAINTAINER_ARCHITECTURE_TOOL",
            schema.VALID_ARCHITECTURE_TOOLS,
        )
    compression_backend = os.getenv("AGENT_MAINTAINER_CONTEXT_COMPRESSION_BACKEND")
    if compression_backend is not None:
        updates["context_compression_backend"] = coercion.as_choice(
            compression_backend,
            "AGENT_MAINTAINER_CONTEXT_COMPRESSION_BACKEND",
            schema.VALID_CONTEXT_COMPRESSION_BACKENDS,
        )


def load_config() -> schema.MaintainerConfig:
    """Load Agent Maintainer configuration from pyproject and environment overrides."""

    config = schema.MaintainerConfig()
    config = apply_pyproject(config, read_pyproject())
    return apply_env(config)
