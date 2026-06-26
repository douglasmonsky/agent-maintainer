"""Configuration schema and constants for guardrail settings."""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_SOURCE_ROOTS = ("src",)
DEFAULT_TEST_ROOTS = ("tests",)
DEFAULT_PACKAGE_PATHS = ("src",)
DEFAULT_COVERAGE_SOURCE = ("src",)
DEFAULT_FILE_LENGTH_PATHS = ("src", "tests", "scripts", ".codex/hooks")
DEFAULT_VULTURE_PATHS = ("src", "tests", "scripts")
DEFAULT_SECRET_SCAN_PROFILES = ("full", "ci")
DEFAULT_SECRET_SCAN_HISTORY_PROFILES = ("security",)
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
        "vulture_paths",
        "pip_audit_args",
        "secret_scan_profiles",
        "secret_scan_history_profiles",
        "source_without_test_change_error_profiles",
    )
)
BOOL_FIELDS = frozenset(
    (
        "require_tests",
        "enable_pip_audit",
        "enable_secret_scanning",
        "enable_wemake",
        "enable_interrogate",
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
class GuardrailConfig:
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
    xenon_max_absolute: str = "B"
    xenon_max_modules: str = "A"
    xenon_max_average: str = "A"
    ruff_max_complexity: int = 10
    pyright_type_checking_mode: str = "standard"
    enable_pip_audit: bool = False
    enable_wemake: bool = False
    pip_audit_args: tuple[str, ...] = ()
    enable_secret_scanning: bool = False
    secret_scanner: str = GITLEAKS_SCANNER
    secret_scan_profiles: tuple[str, ...] = DEFAULT_SECRET_SCAN_PROFILES
    secret_scan_history_profiles: tuple[str, ...] = DEFAULT_SECRET_SCAN_HISTORY_PROFILES
    architecture_tool: str = IMPORT_LINTER_TOOL
    enable_interrogate: bool = False
    interrogate_fail_under: int = 80
    diagnostic_artifacts_enabled: bool = True
    diagnostic_artifacts_dir: str = ".verify-logs"
