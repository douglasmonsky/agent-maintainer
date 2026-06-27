"""Configuration schema and constants for maintenance settings."""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_SOURCE_ROOTS = ("src",)
DEFAULT_TEST_ROOTS = ("tests",)
DEFAULT_PACKAGE_PATHS = ("src",)
DEFAULT_COVERAGE_SOURCE = ("src",)
DEFAULT_FILE_LENGTH_PATHS = ("src", "tests", ".codex/hooks")
DEFAULT_VULTURE_PATHS = ("src", "tests", ".codex/hooks")
DEFAULT_STRUCTURE_IGNORE_PATHS = (
    "tests/**",
    "migrations/**",
    "generated/**",
    ".venv/**",
    "venv/**",
    "**/__pycache__/**",
)
DEFAULT_STRUCTURE_HINT_PATTERNS = (
    r"^maintainer_",
    r"^check_",
    r"^user_",
    r"^course_",
    r"_model$",
    r"_service$",
    r"_repository$",
    r"_client$",
    r"_adapter$",
    r"_parser$",
    r"_loader$",
    r"_schema$",
    r"_executor$",
    r"_reporting$",
    r"^(cli|args|config|models|checks|doctor|executor|reporting)$",
)
DEFAULT_SECRET_SCAN_PROFILES = ("full", "ci")
DEFAULT_SECRET_SCAN_HISTORY_PROFILES = ("security",)
DEFAULT_SEMGREP_PROFILES = ("manual",)
DEFAULT_OSV_SCANNER_ARGS = ("scan", "source", "-r", ".")
DEFAULT_OSV_SCANNER_PROFILES = ("manual",)
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
VALID_MODES = frozenset((CUSTOM_MODE, LEGACY_RATCHET_MODE, FRESH_STRICT_MODE))
IMPORT_LINTER_TOOL = "import-linter"
TACH_TOOL = "tach"
VALID_ARCHITECTURE_TOOLS = frozenset((IMPORT_LINTER_TOOL, TACH_TOOL))
GITLEAKS_SCANNER = "gitleaks"
SUPPORTED_SECRET_SCANNERS = frozenset((GITLEAKS_SCANNER,))

TUPLE_FIELDS = frozenset(
    (
        "source_roots",
        "test_roots",
        "package_paths",
        "coverage_source",
        "file_length_paths",
        "structure_paths",
        "structure_ignore_paths",
        "structure_hint_patterns",
        "vulture_paths",
        "pip_audit_args",
        "mutmut_args",
        "semgrep_args",
        "semgrep_profiles",
        "osv_scanner_args",
        "osv_scanner_profiles",
        "trivy_args",
        "trivy_profiles",
        "sbom_args",
        "sbom_profiles",
        "license_check_args",
        "license_check_profiles",
        "secret_scan_profiles",
        "secret_scan_history_profiles",
        "markdownlint_paths",
        "yamllint_paths",
        "taplo_paths",
        "check_jsonschema_args",
        "source_without_test_change_error_profiles",
    )
)
BOOL_FIELDS = frozenset(
    (
        "require_tests",
        "enable_pip_audit",
        "enable_mutmut",
        "enable_semgrep",
        "enable_osv_scanner",
        "enable_trivy",
        "enable_sbom",
        "enable_license_check",
        "enable_secret_scanning",
        "enable_wemake",
        "enable_interrogate",
        "enable_markdownlint",
        "enable_yamllint",
        "enable_taplo",
        "enable_check_jsonschema",
        "allow_source_without_test_change",
        "diagnostic_artifacts_enabled",
    )
)
INT_FIELDS = frozenset(
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
        "ruff_max_complexity",
        "interrogate_fail_under",
    )
)
STR_FIELDS = frozenset(
    (
        "xenon_max_absolute",
        "xenon_max_modules",
        "xenon_max_average",
        "pyright_type_checking_mode",
        "file_length_baseline",
        "diagnostic_artifacts_dir",
        "secret_scanner",
    )
)


@dataclass(frozen=True)
class MaintainerConfig:
    """Resolved verifier settings after presets and overrides are applied."""

    mode: str = CUSTOM_MODE
    source_roots: tuple[str, ...] = DEFAULT_SOURCE_ROOTS
    test_roots: tuple[str, ...] = DEFAULT_TEST_ROOTS
    package_paths: tuple[str, ...] = DEFAULT_PACKAGE_PATHS
    coverage_source: tuple[str, ...] = DEFAULT_COVERAGE_SOURCE
    file_length_paths: tuple[str, ...] = DEFAULT_FILE_LENGTH_PATHS
    vulture_paths: tuple[str, ...] = DEFAULT_VULTURE_PATHS
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
    suppression_max_new: int = 3
    folder_file_warn: int = 20
    folder_file_block: int = 40
    structure_cluster_min: int = 4
    xenon_max_absolute: str = "B"
    xenon_max_modules: str = "A"
    xenon_max_average: str = "A"
    ruff_max_complexity: int = 10
    pyright_type_checking_mode: str = "standard"
    enable_pip_audit: bool = False
    enable_wemake: bool = False
    pip_audit_args: tuple[str, ...] = ()
    enable_mutmut: bool = False
    mutmut_args: tuple[str, ...] = ("run",)
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
    structure_paths: tuple[str, ...] = ()
    structure_ignore_paths: tuple[str, ...] = DEFAULT_STRUCTURE_IGNORE_PATHS
    structure_hint_patterns: tuple[str, ...] = DEFAULT_STRUCTURE_HINT_PATTERNS
