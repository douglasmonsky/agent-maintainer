"""Tests for guardrail configuration and check catalog construction."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from scripts import guardrail_catalog, guardrail_config
from scripts.guardrail_config import GuardrailConfig
from scripts.guardrail_models import FULL_PROFILE, PRECOMMIT_PROFILE

CONFIG_COVERAGE_THRESHOLD = 91
ENV_COVERAGE_THRESHOLD = 95
STRICT_FILE_LENGTH_MAX_PHYSICAL = 500
STRICT_COMPLEXITY = 8
OVERRIDE_COMPLEXITY = 9


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
coverage_fail_under = 91
architecture_tool = "tach"
""".strip(),
        encoding="utf-8",
    )

    raw = guardrail_config._read_pyproject(pyproject)
    loaded = guardrail_config._apply_pyproject(GuardrailConfig(), raw)

    assert loaded.source_roots == ("lib",)
    assert loaded.test_roots == ("specs",)
    assert loaded.require_tests is True
    assert loaded.enable_pip_audit is True
    assert loaded.pip_audit_args == ("-r", "requirements.txt")
    assert loaded.coverage_fail_under == CONFIG_COVERAGE_THRESHOLD
    assert loaded.architecture_tool == "tach"


def test_invalid_config_values_raise_clear_type_errors() -> None:
    with pytest.raises(TypeError, match="source_roots"):
        guardrail_config._as_tuple(12, "source_roots")

    with pytest.raises(TypeError, match="enable_pip_audit"):
        guardrail_config._as_bool("maybe", "enable_pip_audit")

    with pytest.raises(TypeError, match="coverage_fail_under"):
        guardrail_config._as_int("not-an-int", "coverage_fail_under")

    with pytest.raises(TypeError, match="xenon_max_absolute"):
        guardrail_config._as_str("", "xenon_max_absolute")

    with pytest.raises(TypeError, match="mode"):
        guardrail_config._as_choice("maximum", "mode", guardrail_config.VALID_MODES)

    with pytest.raises(TypeError, match="architecture_tool"):
        guardrail_config._as_choice(
            "layers",
            "architecture_tool",
            guardrail_config.VALID_ARCHITECTURE_TOOLS,
        )


def test_fresh_strict_mode_applies_before_explicit_config() -> None:
    loaded = guardrail_config._apply_pyproject(
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


def test_environment_mode_applies_before_explicit_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GUARDRAILS_MODE", "fresh-strict")
    monkeypatch.setenv("GUARDRAILS_ENABLE_WEMAKE", "false")

    loaded = guardrail_config._apply_env(GuardrailConfig())

    assert loaded.mode == "fresh-strict"
    assert loaded.ruff_max_complexity == STRICT_COMPLEXITY
    assert loaded.enable_wemake is False


def test_environment_overrides_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GUARDRAILS_SOURCE_ROOTS", "pkg,tools")
    monkeypatch.setenv("GUARDRAILS_REQUIRE_TESTS", "false")
    monkeypatch.setenv("GUARDRAILS_COVERAGE_FAIL_UNDER", "95")
    monkeypatch.setenv("GUARDRAILS_PIP_AUDIT_ARGS", "-r requirements.txt")
    monkeypatch.setenv("GUARDRAILS_ARCHITECTURE_TOOL", "tach")

    loaded = guardrail_config._apply_env(GuardrailConfig())

    assert loaded.source_roots == ("pkg", "tools")
    assert loaded.require_tests is False
    assert loaded.coverage_fail_under == ENV_COVERAGE_THRESHOLD
    assert loaded.pip_audit_args == ("-r", "requirements.txt")
    assert loaded.architecture_tool == "tach"


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
    assert FULL_PROFILE in by_name["pip-audit"].profiles
