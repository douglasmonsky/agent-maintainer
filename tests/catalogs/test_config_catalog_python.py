"""Tests for Agent Maintainer configuration and check catalog construction."""

from __future__ import annotations

from dataclasses import replace

from agent_maintainer.catalogs import catalog as maintainer_catalog
from agent_maintainer.catalogs import python as maintainer_catalog_python
from agent_maintainer.config import (
    modes as maintainer_config_modes,
)
from agent_maintainer.core.config import MaintainerConfig


def test_pytest_and_diff_cover_are_required_when_tests_are_required() -> None:
    config = replace(
        MaintainerConfig(),
        test_roots=("tests",),
        coverage_source=("scripts",),
        require_tests=True,
    )

    pytest_check = maintainer_catalog_python.pytest_check(config)
    diff_cover = maintainer_catalog_python.diff_cover_check(config, "origin/main")

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
        MaintainerConfig(),
        diagnostic_artifacts_dir=".custom-logs",
        test_roots=("tests",),
        coverage_source=("scripts",),
        require_tests=True,
    )

    check = maintainer_catalog_python.pytest_check(config)

    assert "--cov-report=xml" in check.command
    assert "--cov-report=json:.custom-logs/coverage.json" in check.command
    assert "--junitxml=.custom-logs/pytest-junit.xml" in check.command
    assert check.artifact_paths == (
        "coverage.xml",
        ".custom-logs/coverage.json",
        ".custom-logs/pytest-junit.xml",
    )


def test_pytest_and_diff_cover_skip_when_tests_are_disabled() -> None:
    config = replace(MaintainerConfig(), require_tests=False)

    pytest_check = maintainer_catalog_python.pytest_check(config)
    diff_cover = maintainer_catalog_python.diff_cover_check(config, "origin/main")

    assert pytest_check.optional_skip_reason
    assert diff_cover.optional_skip_reason


def test_pip_audit_and_wemake_commands_follow_config() -> None:
    disabled = MaintainerConfig()
    enabled = replace(
        MaintainerConfig(),
        enable_pip_audit=True,
        pip_audit_args=("-r", "config/dev-dependencies.txt"),
        enable_wemake=True,
    )

    assert maintainer_catalog_python.pip_audit_check(disabled).optional_skip_reason
    assert maintainer_catalog_python.pip_audit_check(enabled).command == [
        "pip-audit",
        "-r",
        "config/dev-dependencies.txt",
        "--format",
        "json",
        "--output",
        ".verify-logs/pip-audit.json",
    ]
    assert maintainer_catalog_python.pip_audit_check(enabled).artifact_paths == (
        ".verify-logs/pip-audit.json",
    )
    assert maintainer_catalog_python.wemake_check(enabled, ("scripts",)).command == [
        "flake8",
        "--require-plugins",
        "wemake-python-styleguide",
        "scripts",
    ]


def test_interrogate_command_follows_config() -> None:
    disabled = MaintainerConfig()
    enabled = replace(
        MaintainerConfig(),
        enable_interrogate=True,
        interrogate_fail_under=30,
    )

    assert maintainer_catalog_python.interrogate_check(disabled, ("scripts",)).optional_skip_reason
    assert maintainer_catalog_python.interrogate_check(enabled, ("scripts",)).command == [
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
    config = MaintainerConfig(diagnostic_artifacts_dir=".custom-logs")
    checks = maintainer_catalog.make_checks(config, "HEAD", "origin/main")
    pyright = next(check for check in checks if check.name == "pyright")

    assert pyright.command[:3] == [
        maintainer_catalog.sys.executable,
        "-m",
        "agent_maintainer.runners.pyright",
    ]
    assert pyright.artifact_paths == (
        ".custom-logs/pyright.json",
        ".custom-logs/pyrightconfig.generated.json",
    )


def test_pyright_strict_ratchet_is_manual_and_disabled_by_default() -> None:
    """Strict Pyright ratchet is opt-in and manual-profile scoped."""

    config = MaintainerConfig(diagnostic_artifacts_dir=".custom-logs")
    check = maintainer_catalog_python.pyright_strict_ratchet_check(config)

    assert check.name == "pyright-strict-ratchet"
    assert check.profiles == maintainer_catalog.models.MANUAL_PROFILES
    assert check.optional_skip_reason
    assert check.command == [
        maintainer_catalog.sys.executable,
        "-m",
        "agent_maintainer.runners.pyright_strict",
    ]


def test_pyright_strict_ratchet_declares_artifacts_when_enabled() -> None:
    """Enabled strict Pyright ratchet captures strict artifacts."""

    config = MaintainerConfig(
        diagnostic_artifacts_dir=".custom-logs",
        pyright_strict_ratchet_enabled=True,
    )
    check = maintainer_catalog_python.pyright_strict_ratchet_check(config)

    assert check.required_executable == "pyright"
    assert check.optional_skip_reason is None
    assert check.artifact_paths == (
        ".custom-logs/pyright-strict.json",
        ".custom-logs/pyrightconfig.strict.generated.json",
    )


def test_ruff_check_uses_json_artifact_runner() -> None:
    config = MaintainerConfig(diagnostic_artifacts_dir=".custom-logs")
    checks = maintainer_catalog.make_checks(config, "HEAD", "origin/main")
    ruff = next(check for check in checks if check.name == "ruff")

    assert ruff.command[:3] == [
        maintainer_catalog.sys.executable,
        "-m",
        "agent_maintainer.runners.ruff",
    ]
    assert ruff.artifact_paths == (".custom-logs/ruff.json",)


def test_bandit_check_uses_json_artifact_runner() -> None:
    config = MaintainerConfig(diagnostic_artifacts_dir=".custom-logs")
    checks = maintainer_catalog.make_checks(config, "HEAD", "origin/main")
    bandit = next(check for check in checks if check.name == "bandit")

    assert bandit.command[:3] == [
        maintainer_catalog.sys.executable,
        "-m",
        "agent_maintainer.runners.bandit",
    ]
    assert bandit.artifact_paths == (".custom-logs/bandit.json",)


def test_pip_audit_unsafe_config_fails_only_in_fresh_strict() -> None:
    strict = maintainer_config_modes.apply_mode(MaintainerConfig(), "fresh-strict")
    strict = replace(strict, enable_pip_audit=True, pip_audit_args=())
    custom = replace(MaintainerConfig(), enable_pip_audit=True, pip_audit_args=())

    strict_check = maintainer_catalog_python.pip_audit_check(strict)
    custom_check = maintainer_catalog_python.pip_audit_check(custom)

    assert strict_check.command[:3] == [
        maintainer_catalog.sys.executable,
        "-m",
        "agent_maintainer.checks.pip_audit_config",
    ]
    assert custom_check.optional_skip_reason
    assert "pinned input" in custom_check.optional_skip_reason


def test_mutmut_check_passes_result_ratchet_thresholds() -> None:
    """Enabled Mutmut result ratchets are passed to the runner."""

    config = replace(
        MaintainerConfig(),
        enable_mutmut=True,
        mutmut_args=("run",),
        mutmut_result_ratchet_enabled=True,
        mutmut_max_survivors=84,
        mutmut_max_suspicious=0,
        mutmut_max_timeouts=0,
        mutmut_min_score=71,
    )

    check = maintainer_catalog_python.mutmut_check(config)

    assert check.command == [
        maintainer_catalog.sys.executable,
        "-m",
        "agent_maintainer.runners.mutmut",
        "--max-survivors",
        "84",
        "--max-suspicious",
        "0",
        "--max-timeouts",
        "0",
        "--min-score",
        "71",
        "run",
    ]


def test_mutmut_target_ratchet_runs_when_floor_configured() -> None:
    """Mutmut target floor is a cheap full/CI ratchet, not mutation execution."""

    config = replace(MaintainerConfig(), mutmut_target_min=3)

    check = maintainer_catalog_python.mutmut_target_ratchet_check(config)

    assert check.name == "mutmut-target-ratchet"
    assert check.profiles == maintainer_catalog.models.FULL_PROFILES
    assert check.command == [
        maintainer_catalog.sys.executable,
        "-m",
        "agent_maintainer.checks.mutmut_targets",
        "--min-targets",
        "3",
    ]


def test_mutmut_target_ratchet_skips_without_floor() -> None:
    """Default installs do not require explicit Mutmut target floors."""

    check = maintainer_catalog_python.mutmut_target_ratchet_check(MaintainerConfig())

    assert check.optional_skip_reason
    assert "mutmut_target_min = 0" in check.optional_skip_reason
