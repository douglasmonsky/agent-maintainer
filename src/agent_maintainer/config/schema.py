"""Configuration schema and constants for maintenance settings."""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_maintainer.config import schema_fields
from agent_maintainer.config.java import JavaGradleConfig
from agent_maintainer.config.structure_defaults import (
    DEFAULT_STRUCTURE_HINT_PATTERNS,
    DEFAULT_STRUCTURE_IGNORE_PATHS,
)
from agent_maintainer.config.workspaces import WorkspaceConfig

DEFAULT_SOURCE_ROOTS = ("src",)
DEFAULT_TEST_ROOTS = ("tests",)
DEFAULT_PACKAGE_PATHS = ("src",)
DEFAULT_COVERAGE_SOURCE = ("src",)
DEFAULT_FILE_LENGTH_PATHS = ("src", "tests", ".codex/hooks", ".claude/hooks")
DEFAULT_VULTURE_PATHS = ("src", "tests", ".codex/hooks", ".claude/hooks")
DEFAULT_SECRET_SCAN_PROFILES = ("full", "ci")
DEFAULT_SECRET_SCAN_HISTORY_PROFILES = ("security",)
DEFAULT_SEMGREP_PROFILES = ("manual",)
DEFAULT_OSV_SCANNER_ARGS = ("scan", "source", "-r", ".")
DEFAULT_OSV_SCANNER_PROFILES = ("manual",)
DEFAULT_PYRIGHT_STRICT_BASELINE = "config/pyright-strict-baseline.json"
DEFAULT_PYRIGHT_STRICT_PROFILES = ("manual",)
DEFAULT_TRIVY_ARGS = (
    "fs",
    "--scanners",
    "vuln,misconfig",
    "--format",
    "json",
    "--exit-code",
    "1",
    ".",
)
DEFAULT_TRIVY_PROFILES = ("manual",)
DEFAULT_TYPESCRIPT_LINT_PROFILES = ("precommit", "full", "ci")
DEFAULT_TYPESCRIPT_TYPECHECK_PROFILES = ("full", "ci")
DEFAULT_TYPESCRIPT_TEST_PROFILES = ("full", "ci")
DEFAULT_TYPESCRIPT_ADVISORY_SOURCE_WARN_FILES = 4
DEFAULT_TYPESCRIPT_ADVISORY_SOURCE_WARN_LINES = 200
DEFAULT_TS_ADVISORY_BROAD_SUPPRESSION_WARN = 1
DEFAULT_FILE_BASELINE_MODE = "advisory"
DEFAULT_SBOM_ARGS = (
    "requirements",
    "config/dev-lock.txt",
    "--output-reproducible",
    "--of",
    "JSON",
)
DEFAULT_SBOM_PROFILES = ("ci",)
DEFAULT_LICENSE_CHECK_ARGS = ("--from=mixed", "--format=json")
DEFAULT_LICENSE_CHECK_PROFILES = ("manual",)
DEFAULT_MARKDOWNLINT_PATHS = ("**/*.md",)
DEFAULT_YAMLLINT_PATHS = (
    ".github/workflows",
    ".github/dependabot.yml",
    ".pre-commit-config.yaml",
    "*.yml",
    "*.yaml",
)
DEFAULT_TAPLO_PATHS = ("*.toml", "config/*.toml")
DEFAULT_CHECK_JSONSCHEMA_ARGS = ()
CUSTOM_MODE = "custom"
LEGACY_RATCHET_MODE = "legacy-ratchet"
FRESH_STRICT_MODE = "fresh-strict"
IMPORT_LINTER_TOOL = "import-linter"
TACH_TOOL = "tach"
GITLEAKS_SCANNER = "gitleaks"
NONE_COMPRESSION_BACKEND = "none"
TRUNCATE_COMPRESSION_BACKEND = "truncate"
EXTRACTIVE_COMPRESSION_BACKEND = "extractive"
HEADROOM_COMPRESSION_BACKEND = "headroom"

BOOL_FIELDS = schema_fields.BOOL_FIELDS
FLOAT_FIELDS = schema_fields.FLOAT_FIELDS
INT_FIELDS = schema_fields.INT_FIELDS
NON_NEGATIVE_INT_FIELDS = schema_fields.NON_NEGATIVE_INT_FIELDS
STR_FIELDS = schema_fields.STR_FIELDS
TUPLE_FIELDS = schema_fields.TUPLE_FIELDS

VALID_MODES = frozenset((CUSTOM_MODE, LEGACY_RATCHET_MODE, FRESH_STRICT_MODE))
VALID_ARCHITECTURE_TOOLS = frozenset((IMPORT_LINTER_TOOL, TACH_TOOL))
SUPPORTED_SECRET_SCANNERS = frozenset((GITLEAKS_SCANNER,))
VALID_CONTEXT_COMPRESSION_BACKENDS = frozenset(
    (
        NONE_COMPRESSION_BACKEND,
        TRUNCATE_COMPRESSION_BACKEND,
        EXTRACTIVE_COMPRESSION_BACKEND,
        HEADROOM_COMPRESSION_BACKEND,
    )
)
VALID_FILE_BASELINE_MODES = frozenset(("advisory", "blocking"))


@dataclass(frozen=True)
class FileBaselineGroupConfig:
    """One provider-neutral watched file baseline group."""

    name: str
    include: tuple[str, ...]
    exclude: tuple[str, ...] = ()
    role: str = "unknown"
    max_physical_lines: int = 0
    max_nonblank_lines: int = 0
    changed_file_warn: int = 0
    changed_line_warn: int = 0


@dataclass(frozen=True)
class MaintainerConfig:
    """Resolved verifier settings after presets and overrides are applied."""

    mode: str = CUSTOM_MODE
    java: JavaGradleConfig = field(default_factory=JavaGradleConfig)
    workspaces: tuple[WorkspaceConfig, ...] = ()
    source_roots: tuple[str, ...] = DEFAULT_SOURCE_ROOTS
    test_roots: tuple[str, ...] = DEFAULT_TEST_ROOTS
    package_paths: tuple[str, ...] = DEFAULT_PACKAGE_PATHS
    coverage_source: tuple[str, ...] = DEFAULT_COVERAGE_SOURCE
    file_length_paths: tuple[str, ...] = DEFAULT_FILE_LENGTH_PATHS
    vulture_paths: tuple[str, ...] = DEFAULT_VULTURE_PATHS
    file_baselines_enabled: bool = False
    file_baselines_mode: str = DEFAULT_FILE_BASELINE_MODE
    file_baselines: tuple[FileBaselineGroupConfig, ...] = ()
    require_tests: bool = True
    coverage_fail_under: int = 80
    diff_cover_fail_under: int = 90
    file_length_max_physical: int = 600
    file_length_max_source: int = 450
    file_length_baseline: str = ""
    change_warn_lines: int = 300
    change_block_lines: int = 800
    change_warn_files: int = 8
    change_block_files: int = 20
    source_without_test_change_error_profiles: tuple[str, ...] = ()
    allow_source_without_test_change: bool = False
    cohesive_change_override_enabled: bool = False
    cohesive_change_override_paths: tuple[str, ...] = ()
    cohesive_change_override_max_lines: int = 2_000
    cohesive_change_override_max_files: int = 40
    suppression_max_new: int = 3
    folder_file_warn: int = 20
    folder_file_block: int = 40
    structure_cluster_min: int = 4
    xenon_max_absolute: str = "B"
    xenon_max_modules: str = "A"
    xenon_max_average: str = "A"
    ruff_max_complexity: int = 10
    pyright_type_checking_mode: str = "standard"
    pyright_strict_ratchet_enabled: bool = False
    pyright_strict_baseline: str = DEFAULT_PYRIGHT_STRICT_BASELINE
    pyright_strict_max_errors: int = 0
    pyright_strict_profiles: tuple[str, ...] = DEFAULT_PYRIGHT_STRICT_PROFILES
    context_default_budget_chars: int = 12_000
    context_hook_budget_chars: int = 8_000
    context_last_failure_budget_chars: int = 16_000
    context_pack_budget_chars: int = 24_000
    context_large_file_threshold_lines: int = 800
    context_large_file_threshold_bytes: int = 250_000
    context_max_direct_file_read_lines: int = 250
    context_max_direct_log_read_lines: int = 200
    context_max_failure_items: int = 10
    context_max_paths_default: int = 50
    context_write_context_packs: bool = True
    context_packs_local_only: bool = True
    context_pack_contains_source: bool = True
    context_require_outline_for_large_files: bool = True
    context_compression_enabled: bool = False
    context_compression_backend: str = EXTRACTIVE_COMPRESSION_BACKEND
    context_compression_target_ratio: float = 0.5
    context_compression_require_backend: bool = False
    ratchet_enabled: bool = False
    ratchet_baseline_path: str = ".agent-maintainer/ratchet-baseline.json"
    ratchet_guidance_path: str = "AGENTS.ratchet.md"
    ratchet_target_limit: int = 5
    large_changes_enabled: bool = False
    large_change_plan_dirs: tuple[str, ...] = (".agent-maintainer/change-plans",)
    large_change_max_active_plans: int = 1
    large_change_allow_expired_plans: bool = False
    large_change_require_required_sections: bool = True
    large_change_fail_out_of_plan_paths: bool = True
    enable_pip_audit: bool = False
    enable_wemake: bool = False
    pip_audit_args: tuple[str, ...] = ()
    enable_mutmut: bool = False
    mutmut_args: tuple[str, ...] = ("run",)
    mutmut_target_min: int = 0
    mutmut_result_ratchet_enabled: bool = False
    mutmut_max_survivors: int = 0
    mutmut_max_suspicious: int = 0
    mutmut_max_timeouts: int = 0
    mutmut_min_score: int = 0
    enable_semgrep: bool = False
    semgrep_args: tuple[str, ...] = (
        "scan",
        "--config",
        "semgrep.yml",
        "--error",
        "--metrics=off",
        ".",
    )
    semgrep_profiles: tuple[str, ...] = DEFAULT_SEMGREP_PROFILES
    enable_osv_scanner: bool = False
    osv_scanner_args: tuple[str, ...] = DEFAULT_OSV_SCANNER_ARGS
    osv_scanner_profiles: tuple[str, ...] = DEFAULT_OSV_SCANNER_PROFILES
    enable_trivy: bool = False
    trivy_args: tuple[str, ...] = DEFAULT_TRIVY_ARGS
    trivy_profiles: tuple[str, ...] = DEFAULT_TRIVY_PROFILES
    enable_typescript: bool = False
    typescript_lint_command: tuple[str, ...] = ()
    typescript_lint_profiles: tuple[str, ...] = DEFAULT_TYPESCRIPT_LINT_PROFILES
    typescript_typecheck_command: tuple[str, ...] = ()
    typescript_typecheck_profiles: tuple[str, ...] = DEFAULT_TYPESCRIPT_TYPECHECK_PROFILES
    typescript_test_command: tuple[str, ...] = ()
    typescript_test_profiles: tuple[str, ...] = DEFAULT_TYPESCRIPT_TEST_PROFILES
    typescript_advisory_source_warn_files: int = DEFAULT_TYPESCRIPT_ADVISORY_SOURCE_WARN_FILES
    typescript_advisory_source_warn_lines: int = DEFAULT_TYPESCRIPT_ADVISORY_SOURCE_WARN_LINES
    typescript_advisory_broad_suppression_warn: int = DEFAULT_TS_ADVISORY_BROAD_SUPPRESSION_WARN
    enable_sbom: bool = False
    sbom_args: tuple[str, ...] = DEFAULT_SBOM_ARGS
    sbom_profiles: tuple[str, ...] = DEFAULT_SBOM_PROFILES
    enable_license_check: bool = False
    license_check_args: tuple[str, ...] = DEFAULT_LICENSE_CHECK_ARGS
    license_check_profiles: tuple[str, ...] = DEFAULT_LICENSE_CHECK_PROFILES
    enable_secret_scanning: bool = False
    secret_scanner: str = GITLEAKS_SCANNER
    secret_scan_profiles: tuple[str, ...] = DEFAULT_SECRET_SCAN_PROFILES
    secret_scan_history_profiles: tuple[str, ...] = DEFAULT_SECRET_SCAN_HISTORY_PROFILES
    architecture_tool: str = IMPORT_LINTER_TOOL
    enable_interrogate: bool = False
    interrogate_fail_under: int = 80
    enable_markdownlint: bool = False
    markdownlint_paths: tuple[str, ...] = DEFAULT_MARKDOWNLINT_PATHS
    enable_yamllint: bool = False
    yamllint_paths: tuple[str, ...] = DEFAULT_YAMLLINT_PATHS
    enable_taplo: bool = False
    taplo_paths: tuple[str, ...] = DEFAULT_TAPLO_PATHS
    enable_check_jsonschema: bool = False
    check_jsonschema_args: tuple[str, ...] = DEFAULT_CHECK_JSONSCHEMA_ARGS
    diagnostic_artifacts_enabled: bool = True
    diagnostic_artifacts_dir: str = ".verify-logs"
    diagnostic_run_history_limit: int = 10
    runtime_events_enabled: bool = False
    runtime_events_dir: str = ".verify-logs/events"
    runtime_event_history_limit: int = 14
    runtime_event_level: str = "info"
    runtime_events_include_debug: bool = False
    structure_paths: tuple[str, ...] = ()
    structure_ignore_paths: tuple[str, ...] = DEFAULT_STRUCTURE_IGNORE_PATHS
    structure_hint_patterns: tuple[str, ...] = DEFAULT_STRUCTURE_HINT_PATTERNS
