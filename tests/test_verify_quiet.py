"""Tests for the quiet verifier orchestration."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from scripts import guardrail_args, verify_quiet
from scripts.guardrail_config import GuardrailConfig
from scripts.guardrail_models import Check, CheckResult

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


def test_collect_results_stops_on_layout_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    args = verify_quiet.parse_args(["--profile", "precommit"])
    config = replace(GuardrailConfig(), source_roots=("missing",), package_paths=("missing",))

    results = verify_quiet.collect_results(args, config, [])

    assert results[0].name == "guardrail-layout"
    assert results[0].passed is False


def test_optional_skip_policy_can_fail_skips() -> None:
    results = [
        CheckResult(
            "pip-audit",
            passed=True,
            output="disabled",
            skipped=True,
            command=("pip-audit",),
            log_path=".verify-logs/pip-audit.log",
        )
    ]

    converted = verify_quiet.apply_optional_skip_policy(results, fail_on_optional_skip=True)

    assert converted[0].passed is False
    assert converted[0].output == "optional check skipped: disabled"
    assert converted[0].skipped is False
    assert converted[0].command == ("pip-audit",)
    assert converted[0].log_path == ".verify-logs/pip-audit.log"


def test_main_prints_success_with_warning_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "scripts").mkdir()
    monkeypatch.setattr(
        verify_quiet,
        "load_config",
        lambda: replace(
            GuardrailConfig(),
            source_roots=("scripts",),
            package_paths=("scripts",),
            require_tests=False,
        ),
    )
    monkeypatch.setattr(
        verify_quiet,
        "make_checks",
        lambda config, base_ref, compare_branch, staged=False: [
            Check("change-budget", ["true"], frozenset(("fast",)))
        ],
    )
    monkeypatch.setattr(
        verify_quiet,
        "run_check",
        lambda check, log_dir, max_lines, max_chars: CheckResult(
            check.name,
            passed=True,
            output="WARN: source changed without tests",
            warning=True,
        ),
    )

    assert verify_quiet.main(["--profile", "fast"]) == 0

    output = capsys.readouterr().out
    assert "PASS" in output
    assert "WARNINGS:" in output
    assert "change-budget: WARN: source changed without tests" in output


def test_main_prints_success_for_passing_selected_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "scripts").mkdir()

    monkeypatch.setattr(
        verify_quiet,
        "load_config",
        lambda: replace(
            GuardrailConfig(),
            source_roots=("scripts",),
            package_paths=("scripts",),
            require_tests=False,
        ),
    )
    monkeypatch.setattr(
        verify_quiet,
        "make_checks",
        lambda config, base_ref, compare_branch, staged=False: [
            Check("custom", ["true"], frozenset(("fast",)))
        ],
    )
    monkeypatch.setattr(
        verify_quiet,
        "run_check",
        lambda check, log_dir, max_lines, max_chars: CheckResult(check.name, passed=True),
    )

    assert verify_quiet.main(["--profile", "fast"]) == 0
    assert capsys.readouterr().out.strip() == "PASS"


def test_main_writes_artifacts_for_selected_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []
    monkeypatch.chdir(tmp_path)
    (tmp_path / "scripts").mkdir()
    monkeypatch.setattr(
        verify_quiet,
        "load_config",
        lambda: replace(
            GuardrailConfig(),
            source_roots=("scripts",),
            package_paths=("scripts",),
            require_tests=False,
        ),
    )
    monkeypatch.setattr(
        verify_quiet,
        "make_checks",
        lambda config, base_ref, compare_branch, staged=False: [
            Check("custom", ["true"], frozenset(("fast",)))
        ],
    )
    monkeypatch.setattr(
        verify_quiet,
        "run_check",
        lambda check, log_dir, max_lines, max_chars: CheckResult(
            check.name,
            passed=True,
            command=tuple(check.command),
            exit_code=0,
            log_path=str(log_dir / f"{check.name}.log"),
        ),
    )
    monkeypatch.setattr(
        verify_quiet,
        "write_run_artifacts",
        lambda log_dir, context, results: calls.append((log_dir, context, results)),
    )

    assert verify_quiet.main(["--profile", "fast"]) == 0

    assert calls
    log_dir, context, results = calls[0]
    assert log_dir == Path(".verify-logs")
    assert context.profile == "fast"
    assert results[0].name == "custom"


def test_main_skips_artifacts_when_diagnostics_are_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "scripts").mkdir()
    monkeypatch.setattr(
        verify_quiet,
        "load_config",
        lambda: replace(
            GuardrailConfig(),
            source_roots=("scripts",),
            package_paths=("scripts",),
            require_tests=False,
            diagnostic_artifacts_enabled=False,
        ),
    )
    monkeypatch.setattr(
        verify_quiet,
        "make_checks",
        lambda config, base_ref, compare_branch, staged=False: [
            Check("custom", ["true"], frozenset(("fast",)))
        ],
    )
    monkeypatch.setattr(
        verify_quiet,
        "run_check",
        lambda check, log_dir, max_lines, max_chars: CheckResult(check.name, passed=True),
    )
    monkeypatch.setattr(
        verify_quiet,
        "write_run_artifacts",
        lambda log_dir, context, results: pytest.fail("artifacts should be disabled"),
    )

    assert verify_quiet.main(["--profile", "fast"]) == 0
