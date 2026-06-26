"""Tests for guardrail configuration and check catalog construction."""

from __future__ import annotations

from dataclasses import replace

from guardrail_lib.config import (
    modes as guardrail_config_modes,
)
from scripts.guardrail_catalogs import catalog as guardrail_catalog
from scripts.guardrail_catalogs import python as guardrail_catalog_python
from scripts.guardrail_core.config import GuardrailConfig


def test_pytest_and_diff_cover_are_required_when_tests_are_required() -> None:
    config = replace(
        GuardrailConfig(),
        test_roots=("tests",),
        coverage_source=("scripts",),
        require_tests=True,
    )

    pytest_check = guardrail_catalog_python.pytest_check(config)
    diff_cover = guardrail_catalog_python.diff_cover_check(config, "origin/main")

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

    check = guardrail_catalog_python.pytest_check(config)

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

    pytest_check = guardrail_catalog_python.pytest_check(config)
    diff_cover = guardrail_catalog_python.diff_cover_check(config, "origin/main")

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

    assert guardrail_catalog_python.pip_audit_check(disabled).optional_skip_reason
    assert guardrail_catalog_python.pip_audit_check(enabled).command == [
        "pip-audit",
        "-r",
        "config/dev-dependencies.txt",
    ]
    assert guardrail_catalog_python.wemake_check(enabled, ("scripts",)).command == [
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

    assert guardrail_catalog_python.interrogate_check(disabled, ("scripts",)).optional_skip_reason
    assert guardrail_catalog_python.interrogate_check(enabled, ("scripts",)).command == [
        "interrogate",
        "--fail-under=30",
        "--ignore-init-method",
        "--ignore-init-module",
        "--ignore-private",
        "--ignore-semiprivate",
        "--ignore-magic",
        "scripts",
    ]


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


def test_pip_audit_unsafe_config_fails_only_in_fresh_strict() -> None:
    strict = guardrail_config_modes.apply_mode(GuardrailConfig(), "fresh-strict")
    strict = replace(strict, enable_pip_audit=True, pip_audit_args=())
    custom = replace(GuardrailConfig(), enable_pip_audit=True, pip_audit_args=())

    strict_check = guardrail_catalog_python.pip_audit_check(strict)
    custom_check = guardrail_catalog_python.pip_audit_check(custom)

    assert strict_check.command[:3] == [
        guardrail_catalog.sys.executable,
        "-m",
        "scripts.check_pip_audit_config",
    ]
    assert custom_check.optional_skip_reason
    assert "pinned input" in custom_check.optional_skip_reason
