"""Tests for guardrail configuration and check catalog construction."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from guardrail_lib.config import (
    coercion as guardrail_config_coercion,
)
from guardrail_lib.config import (
    loader as guardrail_config_loader,
)
from guardrail_lib.config import (
    modes as guardrail_config_modes,
)
from guardrail_lib.config import (
    schema as guardrail_config_schema,
)
from scripts import (
    guardrail_catalog,
    guardrail_config,
)
from scripts.guardrail_config import GuardrailConfig
from scripts.guardrail_models import CI_PROFILE, PRECOMMIT_PROFILE

CONFIG_COVERAGE_THRESHOLD = 91
ENV_COVERAGE_THRESHOLD = 95
STRICT_FILE_LENGTH_MAX_PHYSICAL = 500
STRICT_COMPLEXITY = 8
OVERRIDE_COMPLEXITY = 9
CONFIG_INTERROGATE_THRESHOLD = 31
ENV_INTERROGATE_THRESHOLD = 33


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
enable_interrogate = true
interrogate_fail_under = 31
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
    assert loaded.enable_interrogate is True
    assert loaded.interrogate_fail_under == CONFIG_INTERROGATE_THRESHOLD
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


def test_legacy_ratchet_mode_sets_file_length_baseline() -> None:
    loaded = guardrail_config_modes.apply_mode(GuardrailConfig(), "legacy-ratchet")
    checks = guardrail_catalog.make_checks(loaded, "HEAD", "origin/main")
    file_length = next(check for check in checks if check.name == "file-length")

    assert loaded.file_length_baseline == ".guardrails/file-length-baseline.json"
    assert "--baseline" in file_length.command
    assert ".guardrails/file-length-baseline.json" in file_length.command


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
    monkeypatch.setenv("GUARDRAILS_SOURCE_ROOTS", "pkg,tools")
    monkeypatch.setenv("GUARDRAILS_REQUIRE_TESTS", "false")
    monkeypatch.setenv("GUARDRAILS_COVERAGE_FAIL_UNDER", "95")
    monkeypatch.setenv("GUARDRAILS_PIP_AUDIT_ARGS", "-r requirements.txt")
    monkeypatch.setenv("GUARDRAILS_ARCHITECTURE_TOOL", "tach")
    monkeypatch.setenv("GUARDRAILS_ENABLE_INTERROGATE", "true")
    monkeypatch.setenv("GUARDRAILS_INTERROGATE_FAIL_UNDER", "33")
    monkeypatch.setenv("GUARDRAILS_FILE_LENGTH_BASELINE", ".guardrails/env-baseline.json")
    monkeypatch.setenv("GUARDRAILS_DIAGNOSTIC_ARTIFACTS_ENABLED", "false")
    monkeypatch.setenv("GUARDRAILS_DIAGNOSTIC_ARTIFACTS_DIR", ".env-verify-logs")

    loaded = guardrail_config_loader.apply_env(GuardrailConfig())

    assert loaded.source_roots == ("pkg", "tools")
    assert loaded.require_tests is False
    assert loaded.coverage_fail_under == ENV_COVERAGE_THRESHOLD
    assert loaded.pip_audit_args == ("-r", "requirements.txt")
    assert loaded.architecture_tool == "tach"
    assert loaded.enable_interrogate is True
    assert loaded.interrogate_fail_under == ENV_INTERROGATE_THRESHOLD
    assert loaded.file_length_baseline == ".guardrails/env-baseline.json"
    assert loaded.diagnostic_artifacts_enabled is False
    assert loaded.diagnostic_artifacts_dir == ".env-verify-logs"


def test_path_matching_handles_roots_and_relative_prefixes() -> None:
    assert guardrail_config.path_matches_roots("./src/app.py", ("src",))
    assert guardrail_config.path_matches_roots("tests/unit/test_app.py", ("tests",))
    assert not guardrail_config.path_matches_roots("docs/app.py", ("src",))


def test_pytest_and_diff_cover_are_required_when_tests_are_required() -> None:
    config = replace(
        GuardrailConfig(),
        test_roots=("tests",),
        coverage_source=("scripts",),
        require_tests=True,
    )

    pytest_check = guardrail_catalog.pytest_check(config)
    diff_cover = guardrail_catalog.diff_cover_check(config, "origin/main")

    assert pytest_check.name == "pytest-coverage"
    assert pytest_check.required_executable == "pytest"
    assert "-p" in pytest_check.command
    assert "no:tach" in pytest_check.command
    assert "--cov=scripts" in pytest_check.command
    assert "tests" in pytest_check.command
    assert diff_cover.required_executable == "diff-cover"
    assert diff_cover.optional_skip_reason is None


def test_pytest_check_declares_structured_test_artifacts() -> None:
    config = replace(
        GuardrailConfig(),
        diagnostic_artifacts_dir=".custom-logs",
        test_roots=("tests",),
        coverage_source=("scripts",),
        require_tests=True,
    )

    check = guardrail_catalog.pytest_check(config)

    assert "--cov-report=xml" in check.command
    assert "--cov-report=json:.custom-logs/coverage.json" in check.command
    assert "--junitxml=.custom-logs/pytest-junit.xml" in check.command
    assert check.artifact_paths == (
        "coverage.xml",
        ".custom-logs/coverage.json",
        ".custom-logs/pytest-junit.xml",
    )


def test_pytest_and_diff_cover_skip_when_tests_are_disabled() -> None:
    config = replace(GuardrailConfig(), require_tests=False)

    pytest_check = guardrail_catalog.pytest_check(config)
    diff_cover = guardrail_catalog.diff_cover_check(config, "origin/main")

    assert pytest_check.optional_skip_reason
    assert diff_cover.optional_skip_reason


def test_pip_audit_and_wemake_commands_follow_config() -> None:
    disabled = GuardrailConfig()
    enabled = replace(
        GuardrailConfig(),
        enable_pip_audit=True,
        pip_audit_args=("-r", "config/dev-dependencies.txt"),
        enable_wemake=True,
    )

    assert guardrail_catalog.pip_audit_check(disabled).optional_skip_reason
    assert guardrail_catalog.pip_audit_check(enabled).command == [
        "pip-audit",
        "-r",
        "config/dev-dependencies.txt",
    ]
    assert guardrail_catalog.wemake_check(enabled, ("scripts",)).command == [
        "flake8",
        "--require-plugins",
        "wemake-python-styleguide",
        "scripts",
    ]


def test_interrogate_command_follows_config() -> None:
    disabled = GuardrailConfig()
    enabled = replace(
        GuardrailConfig(),
        enable_interrogate=True,
        interrogate_fail_under=30,
    )

    assert guardrail_catalog.interrogate_check(disabled, ("scripts",)).optional_skip_reason
    assert guardrail_catalog.interrogate_check(enabled, ("scripts",)).command == [
        "interrogate",
        "--fail-under=30",
        "--ignore-init-method",
        "--ignore-init-module",
        "--ignore-private",
        "--ignore-semiprivate",
        "--ignore-magic",
        "scripts",
    ]


def test_architecture_commands_follow_config() -> None:
    default_checks = guardrail_catalog.architecture_checks(GuardrailConfig())
    tach_checks = guardrail_catalog.architecture_checks(
        replace(GuardrailConfig(), architecture_tool="tach", mode="fresh-strict")
    )
    by_name = {check.name: check for check in tach_checks}

    assert default_checks[0].name == "import-linter"
    assert default_checks[0].command == ["lint-imports"]
    assert by_name["tach-config"].required_paths == ("tach.toml",)
    assert by_name["tach"].command == ["tach", "check", "--exact"]
    assert by_name["tach"].required_paths == ("tach.toml",)


def test_make_checks_includes_expected_profiles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "tests").mkdir()
    config = replace(
        GuardrailConfig(),
        source_roots=("scripts",),
        test_roots=("tests",),
        package_paths=("scripts",),
        file_length_paths=("scripts",),
        require_tests=True,
        enable_pip_audit=True,
    )

    checks = guardrail_catalog.make_checks(config, "HEAD", "origin/main", staged=True)
    by_name = {check.name: check for check in checks}

    assert by_name["change-budget"].command[:3]
    assert "--staged" in by_name["change-budget"].command
    assert PRECOMMIT_PROFILE in by_name["pytest-coverage"].profiles


def test_pyright_check_uses_generated_project_runner() -> None:
    config = GuardrailConfig(diagnostic_artifacts_dir=".custom-logs")
    checks = guardrail_catalog.make_checks(config, "HEAD", "origin/main")
    pyright = next(check for check in checks if check.name == "pyright")

    assert pyright.command[:3] == [
        guardrail_catalog.sys.executable,
        "-m",
        "scripts.run_pyright",
    ]
    assert pyright.artifact_paths == (
        ".custom-logs/pyright.json",
        ".custom-logs/pyrightconfig.generated.json",
    )


def test_ruff_check_uses_json_artifact_runner() -> None:
    config = GuardrailConfig(diagnostic_artifacts_dir=".custom-logs")
    checks = guardrail_catalog.make_checks(config, "HEAD", "origin/main")
    ruff = next(check for check in checks if check.name == "ruff")

    assert ruff.command[:3] == [
        guardrail_catalog.sys.executable,
        "-m",
        "scripts.run_ruff",
    ]
    assert ruff.artifact_paths == (".custom-logs/ruff.json",)


def test_bandit_check_uses_json_artifact_runner() -> None:
    config = GuardrailConfig(diagnostic_artifacts_dir=".custom-logs")
    checks = guardrail_catalog.make_checks(config, "HEAD", "origin/main")
    bandit = next(check for check in checks if check.name == "bandit")

    assert bandit.command[:3] == [
        guardrail_catalog.sys.executable,
        "-m",
        "scripts.run_bandit",
    ]
    assert bandit.artifact_paths == (".custom-logs/bandit.json",)


def test_workflow_checks_are_configured_for_github_actions() -> None:
    checks = guardrail_catalog.workflow_checks()
    by_name = {check.name: check for check in checks}

    assert by_name["actionlint"].command == ["actionlint", "-no-color", "-oneline"]
    assert by_name["actionlint"].required_executable == "actionlint"
    assert by_name["zizmor"].command == [
        "zizmor",
        "--offline",
        "--no-progress",
        ".github/workflows",
        ".github/dependabot.yml",
    ]
    assert by_name["zizmor"].required_executable == "zizmor"


def test_fresh_strict_change_budget_fails_missing_test_change_in_precommit_only() -> None:
    config = guardrail_config_modes.apply_mode(GuardrailConfig(), "fresh-strict")
    checks = guardrail_catalog.make_checks(config, "HEAD", "origin/main")
    precommit = [
        check
        for check in checks
        if check.name == "change-budget" and PRECOMMIT_PROFILE in check.profiles
    ]
    ci = [
        check for check in checks if check.name == "change-budget" and CI_PROFILE in check.profiles
    ]

    assert len(precommit) == 1
    assert "--missing-test-change-as-error" in precommit[0].command
    assert "--missing-test-change-as-error" not in ci[0].command


def test_source_without_test_escape_hatch_reaches_change_budget_command() -> None:
    config = guardrail_config_modes.apply_mode(GuardrailConfig(), "fresh-strict")
    config = replace(config, allow_source_without_test_change=True)
    checks = guardrail_catalog.make_checks(config, "HEAD", "origin/main")
    precommit = next(
        check
        for check in checks
        if check.name == "change-budget" and PRECOMMIT_PROFILE in check.profiles
    )

    assert "--allow-source-without-test-change" in precommit.command


def test_pip_audit_unsafe_config_fails_only_in_fresh_strict() -> None:
    strict = guardrail_config_modes.apply_mode(GuardrailConfig(), "fresh-strict")
    strict = replace(strict, enable_pip_audit=True, pip_audit_args=())
    custom = replace(GuardrailConfig(), enable_pip_audit=True, pip_audit_args=())

    strict_check = guardrail_catalog.pip_audit_check(strict)
    custom_check = guardrail_catalog.pip_audit_check(custom)

    assert strict_check.command[:3] == [
        guardrail_catalog.sys.executable,
        "-m",
        "scripts.check_pip_audit_config",
    ]
    assert custom_check.optional_skip_reason
    assert "pinned input" in custom_check.optional_skip_reason
