"""Tests Agent Maintainer configuration loading and coercion."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer.config import coercion as maintainer_config_coercion
from agent_maintainer.config import loader as maintainer_config_loader
from agent_maintainer.config import modes as maintainer_config_modes
from agent_maintainer.config import schema as maintainer_config_schema
from agent_maintainer.core import config as maintainer_config
from agent_maintainer.core.config import MaintainerConfig

CONFIG_COVERAGE_THRESHOLD = 91
ENV_COVERAGE_THRESHOLD = 95
STRICT_FILE_LENGTH_MAX_PHYSICAL = 500
STRICT_COMPLEXITY = 8
OVERRIDE_COMPLEXITY = 9
CONFIG_INTERROGATE_THRESHOLD = 31
ENV_INTERROGATE_THRESHOLD = 33
CONFIG_OVERRIDE_MAX_LINES = 1_234
CONFIG_OVERRIDE_MAX_FILES = 23
ENV_OVERRIDE_MAX_LINES = 2_345
ENV_OVERRIDE_MAX_FILES = 24
CONFIG_RUN_HISTORY_LIMIT = 7
ENV_RUN_HISTORY_LIMIT = 3
CONFIG_MUTMUT_TARGET_MIN = 3
ENV_MUTMUT_TARGET_MIN = 4


def set_envs(monkeypatch: pytest.MonkeyPatch, values: dict[str, str]) -> None:
    """Set multiple environment variables for config override tests."""

    for name, value in values.items():
        monkeypatch.setenv(name, value)


def test_read_pyproject_loads_ai_maintainer_config(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.agent_maintainer]
source_roots = ["lib"]
test_roots = ["specs"]
require_tests = true
enable_pip_audit = true
pip_audit_args = ["-r", "requirements.txt"]
enable_mutmut = true
mutmut_args = ["run", "agent_maintainer.core.runtime*"]
mutmut_target_min = 3
enable_semgrep = true
semgrep_args = ["scan", "--config", "semgrep.yml", "--metrics=off", "."]
semgrep_profiles = ["manual"]
enable_osv_scanner = true
osv_scanner_args = ["scan", "source", "-r", "."]
osv_scanner_profiles = ["manual"]
enable_trivy = true
trivy_args = ["fs", "--scanners", "vuln,misconfig", "."]
trivy_profiles = ["manual"]
enable_sbom = true
sbom_args = ["requirements", "config/dev-lock.txt", "--of", "JSON"]
sbom_profiles = ["ci"]
enable_license_check = true
license_check_args = ["--from=mixed", "--format=json", "--allow-only=MIT"]
license_check_profiles = ["manual"]
enable_interrogate = true
interrogate_fail_under = 31
enable_markdownlint = true
markdownlint_paths = ["docs/**/*.md"]
enable_yamllint = true
yamllint_paths = [".github/workflows"]
enable_taplo = true
taplo_paths = ["pyproject.toml"]
enable_check_jsonschema = true
check_jsonschema_args = [
  "--builtin-schema",
  "vendor.github-workflows",
  ".github/workflows/verify.yml",
]
cohesive_change_override_enabled = true
cohesive_change_override_paths = ["src/**", ".codex/hooks/**"]
cohesive_change_override_max_lines = 1234
cohesive_change_override_max_files = 23
coverage_fail_under = 91
file_length_baseline = ".agent-maintainer/baseline.json"
architecture_tool = "tach"

[tool.agent_maintainer.diagnostics]
enabled = false
log_dir = ".custom-verify-logs"
run_history_limit = 7
""".strip(),
        encoding="utf-8",
    )

    raw = maintainer_config_loader.read_pyproject(pyproject)
    loaded = maintainer_config_loader.apply_pyproject(MaintainerConfig(), raw)

    assert loaded.source_roots == ("lib",)
    assert loaded.test_roots == ("specs",)
    assert loaded.require_tests is True
    assert loaded.enable_pip_audit is True
    assert loaded.pip_audit_args == ("-r", "requirements.txt")
    assert loaded.enable_mutmut is True
    assert loaded.mutmut_args == ("run", "agent_maintainer.core.runtime*")
    assert loaded.mutmut_target_min == CONFIG_MUTMUT_TARGET_MIN
    assert loaded.enable_semgrep is True
    assert loaded.semgrep_args == ("scan", "--config", "semgrep.yml", "--metrics=off", ".")
    assert loaded.semgrep_profiles == ("manual",)
    assert loaded.enable_osv_scanner is True
    assert loaded.osv_scanner_args == ("scan", "source", "-r", ".")
    assert loaded.osv_scanner_profiles == ("manual",)
    assert loaded.enable_trivy is True
    assert loaded.trivy_args == ("fs", "--scanners", "vuln,misconfig", ".")
    assert loaded.trivy_profiles == ("manual",)
    assert loaded.enable_sbom is True
    assert loaded.sbom_args == ("requirements", "config/dev-lock.txt", "--of", "JSON")
    assert loaded.sbom_profiles == ("ci",)
    assert loaded.enable_license_check is True
    assert loaded.license_check_args == (
        "--from=mixed",
        "--format=json",
        "--allow-only=MIT",
    )
    assert loaded.license_check_profiles == ("manual",)
    assert loaded.enable_interrogate is True
    assert loaded.interrogate_fail_under == CONFIG_INTERROGATE_THRESHOLD
    assert loaded.enable_markdownlint is True
    assert loaded.markdownlint_paths == ("docs/**/*.md",)
    assert loaded.enable_yamllint is True
    assert loaded.yamllint_paths == (".github/workflows",)
    assert loaded.enable_taplo is True
    assert loaded.taplo_paths == ("pyproject.toml",)
    assert loaded.enable_check_jsonschema is True
    assert loaded.check_jsonschema_args == (
        "--builtin-schema",
        "vendor.github-workflows",
        ".github/workflows/verify.yml",
    )
    assert loaded.cohesive_change_override_enabled is True
    assert loaded.cohesive_change_override_paths == ("src/**", ".codex/hooks/**")
    assert loaded.cohesive_change_override_max_lines == CONFIG_OVERRIDE_MAX_LINES
    assert loaded.cohesive_change_override_max_files == CONFIG_OVERRIDE_MAX_FILES
    assert loaded.coverage_fail_under == CONFIG_COVERAGE_THRESHOLD
    assert loaded.file_length_baseline == ".agent-maintainer/baseline.json"
    assert loaded.architecture_tool == "tach"
    assert loaded.diagnostic_artifacts_enabled is False
    assert loaded.diagnostic_artifacts_dir == ".custom-verify-logs"
    assert loaded.diagnostic_run_history_limit == CONFIG_RUN_HISTORY_LIMIT


def test_invalid_config_values_raise_clear_type_errors() -> None:
    with pytest.raises(TypeError, match="source_roots"):
        maintainer_config_coercion.as_tuple(12, "source_roots")
    with pytest.raises(TypeError, match="enable_pip_audit"):
        maintainer_config_coercion.as_bool("maybe", "enable_pip_audit")
    with pytest.raises(TypeError, match="coverage_fail_under"):
        maintainer_config_coercion.as_int("not-an-int", "coverage_fail_under")
    with pytest.raises(TypeError, match="coverage_fail_under"):
        maintainer_config_coercion.as_int(object(), "coverage_fail_under")
    with pytest.raises(TypeError, match="xenon_max_absolute"):
        maintainer_config_coercion.as_str("", "xenon_max_absolute")
    with pytest.raises(TypeError, match="mode"):
        maintainer_config_coercion.as_choice(
            "maximum", "mode", maintainer_config_schema.VALID_MODES
        )
    with pytest.raises(TypeError, match="architecture_tool"):
        maintainer_config_coercion.as_choice(
            "layers",
            "architecture_tool",
            maintainer_config_schema.VALID_ARCHITECTURE_TOOLS,
        )


def test_fresh_strict_mode_applies_before_explicit_config() -> None:
    loaded = maintainer_config_loader.apply_pyproject(
        MaintainerConfig(),
        {
            "mode": "fresh-strict",
            "ruff_max_complexity": 9,
            "enable_wemake": False,
        },
    )

    assert loaded.mode == "fresh-strict"
    assert loaded.file_length_max_physical == STRICT_FILE_LENGTH_MAX_PHYSICAL
    assert loaded.ruff_max_complexity == OVERRIDE_COMPLEXITY
    assert loaded.enable_wemake is False
    assert loaded.enable_interrogate is True


def test_config_facade_preserves_public_entrypoints() -> None:
    assert maintainer_config.load_config is maintainer_config_loader.load_config
    assert maintainer_config.apply_mode is maintainer_config_modes.apply_mode
    assert maintainer_config.MaintainerConfig is maintainer_config_schema.MaintainerConfig


def test_environment_mode_applies_before_explicit_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_MAINTAINER_MODE", "fresh-strict")
    monkeypatch.setenv("AGENT_MAINTAINER_ENABLE_WEMAKE", "false")

    loaded = maintainer_config_loader.apply_env(MaintainerConfig())

    assert loaded.mode == "fresh-strict"
    assert loaded.ruff_max_complexity == STRICT_COMPLEXITY
    assert loaded.enable_wemake is False


def test_environment_overrides_config(monkeypatch: pytest.MonkeyPatch) -> None:
    set_envs(
        monkeypatch,
        {
            "AGENT_MAINTAINER_SOURCE_ROOTS": "pkg,tools",
            "AGENT_MAINTAINER_REQUIRE_TESTS": "false",
            "AGENT_MAINTAINER_COVERAGE_FAIL_UNDER": "95",
            "AGENT_MAINTAINER_PIP_AUDIT_ARGS": "-r requirements.txt",
            "AGENT_MAINTAINER_ENABLE_MUTMUT": "true",
            "AGENT_MAINTAINER_MUTMUT_ARGS": "run,agent_maintainer.core.runtime*",
            "AGENT_MAINTAINER_ENABLE_SEMGREP": "true",
            "AGENT_MAINTAINER_SEMGREP_ARGS": "scan,--config,semgrep.yml",
            "AGENT_MAINTAINER_SEMGREP_PROFILES": "manual,security",
            "AGENT_MAINTAINER_ENABLE_OSV_SCANNER": "true",
            "AGENT_MAINTAINER_OSV_SCANNER_ARGS": "scan source -r .",
            "AGENT_MAINTAINER_OSV_SCANNER_PROFILES": "manual",
            "AGENT_MAINTAINER_ENABLE_TRIVY": "true",
            "AGENT_MAINTAINER_TRIVY_ARGS": "fs --scanners vuln,misconfig .",
            "AGENT_MAINTAINER_TRIVY_PROFILES": "manual",
            "AGENT_MAINTAINER_ENABLE_SBOM": "true",
            "AGENT_MAINTAINER_SBOM_ARGS": "requirements,config/dev-lock.txt,--of,JSON",
            "AGENT_MAINTAINER_SBOM_PROFILES": "ci",
            "AGENT_MAINTAINER_ENABLE_LICENSE_CHECK": "true",
            "AGENT_MAINTAINER_LICENSE_CHECK_ARGS": ("--from=mixed,--format=json,--allow-only=MIT"),
            "AGENT_MAINTAINER_LICENSE_CHECK_PROFILES": "manual",
            "AGENT_MAINTAINER_ENABLE_SECRET_SCANNING": "true",
            "AGENT_MAINTAINER_SECRET_SCANNER": "gitleaks",
            "AGENT_MAINTAINER_SECRET_SCAN_PROFILES": "full,ci",
            "AGENT_MAINTAINER_ARCHITECTURE_TOOL": "tach",
            "AGENT_MAINTAINER_ENABLE_INTERROGATE": "true",
            "AGENT_MAINTAINER_INTERROGATE_FAIL_UNDER": "33",
            "AGENT_MAINTAINER_ENABLE_MARKDOWNLINT": "true",
            "AGENT_MAINTAINER_MARKDOWNLINT_PATHS": "README.md,docs",
            "AGENT_MAINTAINER_ENABLE_YAMLLINT": "true",
            "AGENT_MAINTAINER_YAMLLINT_PATHS": ".github/workflows",
            "AGENT_MAINTAINER_ENABLE_TAPLO": "true",
            "AGENT_MAINTAINER_TAPLO_PATHS": "pyproject.toml,tach.toml",
            "AGENT_MAINTAINER_ENABLE_CHECK_JSONSCHEMA": "true",
            "AGENT_MAINTAINER_CHECK_JSONSCHEMA_ARGS": (
                "--builtin-schema,vendor.github-workflows,.github/workflows/verify.yml"
            ),
            "AGENT_MAINTAINER_COHESIVE_CHANGE_OVERRIDE_ENABLED": "true",
            "AGENT_MAINTAINER_COHESIVE_CHANGE_OVERRIDE_PATHS": "src/**,.codex/hooks/**",
            "AGENT_MAINTAINER_COHESIVE_CHANGE_OVERRIDE_MAX_LINES": str(
                ENV_OVERRIDE_MAX_LINES,
            ),
            "AGENT_MAINTAINER_COHESIVE_CHANGE_OVERRIDE_MAX_FILES": str(
                ENV_OVERRIDE_MAX_FILES,
            ),
            "AGENT_MAINTAINER_MUTMUT_TARGET_MIN": str(ENV_MUTMUT_TARGET_MIN),
        },
    )
    monkeypatch.setenv(
        "AGENT_MAINTAINER_FILE_LENGTH_BASELINE",
        ".agent-maintainer/env-baseline.json",
    )
    monkeypatch.setenv("AGENT_MAINTAINER_DIAGNOSTIC_ARTIFACTS_ENABLED", "false")
    monkeypatch.setenv("AGENT_MAINTAINER_DIAGNOSTIC_ARTIFACTS_DIR", ".env-verify-logs")
    monkeypatch.setenv(
        "AGENT_MAINTAINER_DIAGNOSTIC_RUN_HISTORY_LIMIT",
        str(ENV_RUN_HISTORY_LIMIT),
    )

    loaded = maintainer_config_loader.apply_env(MaintainerConfig())

    assert loaded.source_roots == ("pkg", "tools")
    assert loaded.require_tests is False
    assert loaded.coverage_fail_under == ENV_COVERAGE_THRESHOLD
    assert loaded.pip_audit_args == ("-r", "requirements.txt")
    assert loaded.enable_mutmut is True
    assert loaded.mutmut_args == ("run", "agent_maintainer.core.runtime*")
    assert loaded.mutmut_target_min == ENV_MUTMUT_TARGET_MIN
    assert loaded.enable_semgrep is True
    assert loaded.semgrep_args == ("scan", "--config", "semgrep.yml")
    assert loaded.semgrep_profiles == ("manual", "security")
    assert loaded.enable_osv_scanner is True
    assert loaded.osv_scanner_args == ("scan", "source", "-r", ".")
    assert loaded.osv_scanner_profiles == ("manual",)
    assert loaded.enable_trivy is True
    assert loaded.trivy_args == ("fs", "--scanners", "vuln,misconfig", ".")
    assert loaded.trivy_profiles == ("manual",)
    assert loaded.enable_sbom is True
    assert loaded.sbom_args == ("requirements", "config/dev-lock.txt", "--of", "JSON")
    assert loaded.sbom_profiles == ("ci",)
    assert loaded.enable_license_check is True
    assert loaded.license_check_args == (
        "--from=mixed",
        "--format=json",
        "--allow-only=MIT",
    )
    assert loaded.license_check_profiles == ("manual",)
    assert loaded.enable_secret_scanning is True
    assert loaded.secret_scanner == "gitleaks"
    assert loaded.secret_scan_profiles == ("full", "ci")
    assert loaded.architecture_tool == "tach"
    assert loaded.enable_interrogate is True
    assert loaded.interrogate_fail_under == ENV_INTERROGATE_THRESHOLD
    assert loaded.enable_markdownlint is True
    assert loaded.markdownlint_paths == ("README.md", "docs")
    assert loaded.enable_yamllint is True
    assert loaded.yamllint_paths == (".github/workflows",)
    assert loaded.enable_taplo is True
    assert loaded.taplo_paths == ("pyproject.toml", "tach.toml")
    assert loaded.enable_check_jsonschema is True
    assert loaded.check_jsonschema_args == (
        "--builtin-schema",
        "vendor.github-workflows",
        ".github/workflows/verify.yml",
    )
    assert loaded.cohesive_change_override_enabled is True
    assert loaded.cohesive_change_override_paths == ("src/**", ".codex/hooks/**")
    assert loaded.cohesive_change_override_max_lines == ENV_OVERRIDE_MAX_LINES
    assert loaded.cohesive_change_override_max_files == ENV_OVERRIDE_MAX_FILES
    assert loaded.file_length_baseline == ".agent-maintainer/env-baseline.json"
    assert loaded.diagnostic_artifacts_enabled is False
    assert loaded.diagnostic_artifacts_dir == ".env-verify-logs"
    assert loaded.diagnostic_run_history_limit == ENV_RUN_HISTORY_LIMIT
