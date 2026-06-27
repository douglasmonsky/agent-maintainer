"""Tests for the quiet verifier orchestration."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ai_guardrails.core import args as guardrail_args
from ai_guardrails.core.config import GuardrailConfig
from ai_guardrails.verify import quiet as verify_quiet

CLI_COVERAGE_THRESHOLD = 92
CLI_INTERROGATE_THRESHOLD = 30
STRICT_COMPLEXITY = 8


def test_parse_csv_like_normalizes_repeated_values() -> None:
    assert guardrail_args.parse_csv_like(["src, tests", "tools/"]) == (
        "src",
        "tests",
        "tools",
    )
    assert guardrail_args.parse_csv_like(None) is None
    assert guardrail_args.parse_csv_like([" , "]) is None


def test_cli_overrides_replace_config_values() -> None:
    args = guardrail_args.parse_args(
        [
            "--source-root",
            "lib",
            "--test-root",
            "specs",
            "--coverage-fail-under",
            "92",
            "--enable-pip-audit",
            "--enable-mutmut",
            "--mutmut-arg",
            "run",
            "--mutmut-arg",
            "ai_guardrails.core.runtime*",
            "--enable-semgrep",
            "--semgrep-arg",
            "scan",
            "--semgrep-arg=--config,semgrep.yml",
            "--semgrep-profile",
            "manual,security",
            "--enable-secret-scanning",
            "--secret-scanner",
            "gitleaks",
            "--secret-scan-profile",
            "full,ci",
            "--secret-scan-history-profile",
            "security",
            "--enable-interrogate",
            "--interrogate-fail-under",
            "30",
            "--enable-markdownlint",
            "--markdownlint-path",
            "README.md,docs",
            "--enable-yamllint",
            "--yamllint-path",
            ".github/workflows",
            "--enable-taplo",
            "--taplo-path",
            "pyproject.toml",
            "--enable-check-jsonschema",
            "--check-jsonschema-arg=--builtin-schema,vendor.github-workflows,.github/workflows/verify.yml",
        ]
    )

    config = guardrail_args.apply_cli_overrides(GuardrailConfig(), args)

    assert config.source_roots == ("lib",)
    assert config.test_roots == ("specs",)
    assert config.coverage_fail_under == CLI_COVERAGE_THRESHOLD
    assert config.enable_pip_audit is True
    assert config.enable_mutmut is True
    assert config.mutmut_args == ("run", "ai_guardrails.core.runtime*")
    assert config.enable_semgrep is True
    assert config.semgrep_args == ("scan", "--config", "semgrep.yml")
    assert config.semgrep_profiles == ("manual", "security")
    assert config.enable_secret_scanning is True
    assert config.secret_scanner == "gitleaks"
    assert config.secret_scan_profiles == ("full", "ci")
    assert config.secret_scan_history_profiles == ("security",)
    assert config.enable_interrogate is True
    assert config.interrogate_fail_under == CLI_INTERROGATE_THRESHOLD
    assert config.enable_markdownlint is True
    assert config.markdownlint_paths == ("README.md", "docs")
    assert config.enable_yamllint is True
    assert config.yamllint_paths == (".github/workflows",)
    assert config.enable_taplo is True
    assert config.taplo_paths == ("pyproject.toml",)
    assert config.enable_check_jsonschema is True
    assert config.check_jsonschema_args == (
        "--builtin-schema",
        "vendor.github-workflows",
        ".github/workflows/verify.yml",
    )


def test_cli_mode_applies_before_other_cli_overrides() -> None:
    args = guardrail_args.parse_args(
        [
            "--mode",
            "fresh-strict",
            "--disable-wemake",
            "--coverage-fail-under",
            "92",
        ]
    )

    config = guardrail_args.apply_cli_overrides(GuardrailConfig(), args)

    assert config.mode == "fresh-strict"
    assert config.ruff_max_complexity == STRICT_COMPLEXITY
    assert config.enable_wemake is False
    assert config.enable_interrogate is True
    assert config.coverage_fail_under == CLI_COVERAGE_THRESHOLD


def test_layout_failures_require_tests_when_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "scripts").mkdir()
    config = replace(
        GuardrailConfig(),
        source_roots=("scripts",),
        package_paths=("scripts",),
        test_roots=("tests",),
        require_tests=True,
    )

    failures = verify_quiet.layout_failures(config, "precommit")

    assert any("test root" in failure for failure in failures)


def test_layout_failures_validate_pyright_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "scripts").mkdir()
    config = replace(
        GuardrailConfig(),
        source_roots=("scripts",),
        package_paths=("scripts",),
        require_tests=False,
        pyright_type_checking_mode="maximum",
    )

    assert verify_quiet.layout_failures(config, "full") == [
        "pyright_type_checking_mode must be one of: basic, off, standard, strict"
    ]
