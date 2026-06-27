"""Tests guardrail configuration loading and coercion."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_guardrails.config import coercion as guardrail_config_coercion
from ai_guardrails.config import loader as guardrail_config_loader
from ai_guardrails.config import modes as guardrail_config_modes
from ai_guardrails.config import schema as guardrail_config_schema
from ai_guardrails.core import config as guardrail_config
from ai_guardrails.core.config import GuardrailConfig

CONFIG_COVERAGE_THRESHOLD = 91
ENV_COVERAGE_THRESHOLD = 95
STRICT_FILE_LENGTH_MAX_PHYSICAL = 500
STRICT_COMPLEXITY = 8
OVERRIDE_COMPLEXITY = 9
CONFIG_INTERROGATE_THRESHOLD = 31
ENV_INTERROGATE_THRESHOLD = 33


def set_envs(monkeypatch: pytest.MonkeyPatch, values: dict[str, str]) -> None:
    """Set multiple environment variables for config override tests."""

    for name, value in values.items():
        monkeypatch.setenv(name, value)


def test_read_pyproject_loads_ai_guardrail_config(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.ai_guardrails]
source_roots = ["lib"]
test_roots = ["specs"]
require_tests = true
enable_pip_audit = true
pip_audit_args = ["-r", "requirements.txt"]
enable_mutmut = true
mutmut_args = ["run", "ai_guardrails.core.runtime*"]
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
coverage_fail_under = 91
file_length_baseline = ".guardrails/baseline.json"
architecture_tool = "tach"

[tool.ai_guardrails.diagnostics]
enabled = false
log_dir = ".custom-verify-logs"
""".strip(),
        encoding="utf-8",
    )

    raw = guardrail_config_loader.read_pyproject(pyproject)
    loaded = guardrail_config_loader.apply_pyproject(GuardrailConfig(), raw)

    assert loaded.source_roots == ("lib",)
    assert loaded.test_roots == ("specs",)
    assert loaded.require_tests is True
    assert loaded.enable_pip_audit is True
    assert loaded.pip_audit_args == ("-r", "requirements.txt")
    assert loaded.enable_mutmut is True
    assert loaded.mutmut_args == ("run", "ai_guardrails.core.runtime*")
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
    assert loaded.coverage_fail_under == CONFIG_COVERAGE_THRESHOLD
    assert loaded.file_length_baseline == ".guardrails/baseline.json"
    assert loaded.architecture_tool == "tach"
    assert loaded.diagnostic_artifacts_enabled is False
    assert loaded.diagnostic_artifacts_dir == ".custom-verify-logs"


def test_invalid_config_values_raise_clear_type_errors() -> None:
    with pytest.raises(TypeError, match="source_roots"):
        guardrail_config_coercion.as_tuple(12, "source_roots")
    with pytest.raises(TypeError, match="enable_pip_audit"):
        guardrail_config_coercion.as_bool("maybe", "enable_pip_audit")
    with pytest.raises(TypeError, match="coverage_fail_under"):
        guardrail_config_coercion.as_int("not-an-int", "coverage_fail_under")
    with pytest.raises(TypeError, match="coverage_fail_under"):
        guardrail_config_coercion.as_int(object(), "coverage_fail_under")
    with pytest.raises(TypeError, match="xenon_max_absolute"):
        guardrail_config_coercion.as_str("", "xenon_max_absolute")
    with pytest.raises(TypeError, match="mode"):
        guardrail_config_coercion.as_choice("maximum", "mode", guardrail_config_schema.VALID_MODES)
    with pytest.raises(TypeError, match="architecture_tool"):
        guardrail_config_coercion.as_choice(
            "layers",
            "architecture_tool",
            guardrail_config_schema.VALID_ARCHITECTURE_TOOLS,
        )


def test_fresh_strict_mode_applies_before_explicit_config() -> None:
    loaded = guardrail_config_loader.apply_pyproject(
        GuardrailConfig(),
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
    assert guardrail_config.load_config is guardrail_config_loader.load_config
    assert guardrail_config.apply_mode is guardrail_config_modes.apply_mode
    assert guardrail_config.GuardrailConfig is guardrail_config_schema.GuardrailConfig


def test_environment_mode_applies_before_explicit_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GUARDRAILS_MODE", "fresh-strict")
    monkeypatch.setenv("GUARDRAILS_ENABLE_WEMAKE", "false")

    loaded = guardrail_config_loader.apply_env(GuardrailConfig())

    assert loaded.mode == "fresh-strict"
    assert loaded.ruff_max_complexity == STRICT_COMPLEXITY
    assert loaded.enable_wemake is False


def test_environment_overrides_config(monkeypatch: pytest.MonkeyPatch) -> None:
    set_envs(
        monkeypatch,
        {
            "GUARDRAILS_SOURCE_ROOTS": "pkg,tools",
            "GUARDRAILS_REQUIRE_TESTS": "false",
            "GUARDRAILS_COVERAGE_FAIL_UNDER": "95",
            "GUARDRAILS_PIP_AUDIT_ARGS": "-r requirements.txt",
            "GUARDRAILS_ENABLE_MUTMUT": "true",
            "GUARDRAILS_MUTMUT_ARGS": "run,ai_guardrails.core.runtime*",
            "GUARDRAILS_ENABLE_SEMGREP": "true",
            "GUARDRAILS_SEMGREP_ARGS": "scan,--config,semgrep.yml",
            "GUARDRAILS_SEMGREP_PROFILES": "manual,security",
            "GUARDRAILS_ENABLE_OSV_SCANNER": "true",
            "GUARDRAILS_OSV_SCANNER_ARGS": "scan source -r .",
            "GUARDRAILS_OSV_SCANNER_PROFILES": "manual",
            "GUARDRAILS_ENABLE_TRIVY": "true",
            "GUARDRAILS_TRIVY_ARGS": "fs --scanners vuln,misconfig .",
            "GUARDRAILS_TRIVY_PROFILES": "manual",
            "GUARDRAILS_ENABLE_SBOM": "true",
            "GUARDRAILS_SBOM_ARGS": "requirements,config/dev-lock.txt,--of,JSON",
            "GUARDRAILS_SBOM_PROFILES": "ci",
            "GUARDRAILS_ENABLE_LICENSE_CHECK": "true",
            "GUARDRAILS_LICENSE_CHECK_ARGS": ("--from=mixed,--format=json,--allow-only=MIT"),
            "GUARDRAILS_LICENSE_CHECK_PROFILES": "manual",
            "GUARDRAILS_ENABLE_SECRET_SCANNING": "true",
            "GUARDRAILS_SECRET_SCANNER": "gitleaks",
            "GUARDRAILS_SECRET_SCAN_PROFILES": "full,ci",
            "GUARDRAILS_ARCHITECTURE_TOOL": "tach",
            "GUARDRAILS_ENABLE_INTERROGATE": "true",
            "GUARDRAILS_INTERROGATE_FAIL_UNDER": "33",
            "GUARDRAILS_ENABLE_MARKDOWNLINT": "true",
            "GUARDRAILS_MARKDOWNLINT_PATHS": "README.md,docs",
            "GUARDRAILS_ENABLE_YAMLLINT": "true",
            "GUARDRAILS_YAMLLINT_PATHS": ".github/workflows",
            "GUARDRAILS_ENABLE_TAPLO": "true",
            "GUARDRAILS_TAPLO_PATHS": "pyproject.toml,tach.toml",
            "GUARDRAILS_ENABLE_CHECK_JSONSCHEMA": "true",
            "GUARDRAILS_CHECK_JSONSCHEMA_ARGS": (
                "--builtin-schema,vendor.github-workflows,.github/workflows/verify.yml"
            ),
        },
    )
    monkeypatch.setenv("GUARDRAILS_FILE_LENGTH_BASELINE", ".guardrails/env-baseline.json")
    monkeypatch.setenv("GUARDRAILS_DIAGNOSTIC_ARTIFACTS_ENABLED", "false")
    monkeypatch.setenv("GUARDRAILS_DIAGNOSTIC_ARTIFACTS_DIR", ".env-verify-logs")

    loaded = guardrail_config_loader.apply_env(GuardrailConfig())

    assert loaded.source_roots == ("pkg", "tools")
    assert loaded.require_tests is False
    assert loaded.coverage_fail_under == ENV_COVERAGE_THRESHOLD
    assert loaded.pip_audit_args == ("-r", "requirements.txt")
    assert loaded.enable_mutmut is True
    assert loaded.mutmut_args == ("run", "ai_guardrails.core.runtime*")
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
    assert loaded.file_length_baseline == ".guardrails/env-baseline.json"
    assert loaded.diagnostic_artifacts_enabled is False
    assert loaded.diagnostic_artifacts_dir == ".env-verify-logs"
