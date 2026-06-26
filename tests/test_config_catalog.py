"""Tests for guardrail configuration and check catalog construction."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from guardrail_lib.config import (
    modes as guardrail_config_modes,
)
from scripts.guardrail_catalogs import catalog as guardrail_catalog
from scripts.guardrail_core import config as guardrail_config
from scripts.guardrail_core.config import GuardrailConfig
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
