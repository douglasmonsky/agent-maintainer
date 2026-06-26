"""Tests for guardrail configuration and check catalog construction."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from guardrail_lib.config import (
    modes as guardrail_config_modes,
)
from scripts import (
    guardrail_catalog,
    guardrail_config,
)
from scripts.guardrail_config import GuardrailConfig
from scripts.guardrail_models import (
    CI_PROFILE,
    FULL_PROFILE,
    FULL_PROFILES,
    MANUAL_PROFILE,
    MANUAL_PROFILES,
    PRECOMMIT_PROFILE,
    VALID_PROFILES,
)


def test_legacy_ratchet_mode_sets_file_length_baseline() -> None:
    loaded = guardrail_config_modes.apply_mode(GuardrailConfig(), "legacy-ratchet")
    checks = guardrail_catalog.make_checks(loaded, "HEAD", "origin/main")
    file_length = next(check for check in checks if check.name == "file-length")

    assert loaded.file_length_baseline == ".guardrails/file-length-baseline.json"
    assert "--baseline" in file_length.command
    assert ".guardrails/file-length-baseline.json" in file_length.command


def test_manual_profile_is_valid_but_separate_from_full_profiles() -> None:
    assert MANUAL_PROFILE in VALID_PROFILES
    assert MANUAL_PROFILES.issubset(VALID_PROFILES)
    assert len(MANUAL_PROFILES) == 1
    assert MANUAL_PROFILE not in FULL_PROFILES
    assert FULL_PROFILE not in MANUAL_PROFILES


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


def test_secret_scan_checks_are_disabled_by_default() -> None:
    checks = guardrail_catalog.make_checks(GuardrailConfig(), "HEAD", "origin/main")
    secret_scan = next(check for check in checks if check.name == "secret-scan")

    assert secret_scan.optional_skip_reason is not None
    assert secret_scan.required_executable is None


def test_secret_scan_checks_use_gitleaks_backend_when_enabled() -> None:
    config = GuardrailConfig(
        enable_secret_scanning=True,
        secret_scan_profiles=("full", "ci"),
        secret_scan_history_profiles=("security",),
    )
    checks = guardrail_catalog.make_checks(config, "origin/main", "origin/main")
    by_profile = {
        next(iter(check.profiles)): check for check in checks if check.name == "secret-scan"
    }
    history = next(check for check in checks if check.name == "secret-scan-history")

    assert by_profile["full"].required_executable == "gitleaks"
    assert "--mode" in by_profile["full"].command
    assert "current-tree" in by_profile["full"].command
    assert "range" in by_profile["ci"].command
    assert history.profiles == frozenset(("security",))
    assert "history" in history.command


def test_secret_scan_checks_use_staged_mode_for_staged_precommit() -> None:
    config = GuardrailConfig(
        enable_secret_scanning=True,
        secret_scan_profiles=(PRECOMMIT_PROFILE,),
    )
    checks = guardrail_catalog.make_checks(config, "HEAD", "origin/main", staged=True)
    secret_scan = next(
        check
        for check in checks
        if check.name == "secret-scan" and PRECOMMIT_PROFILE in check.profiles
    )

    assert "staged" in secret_scan.command


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
