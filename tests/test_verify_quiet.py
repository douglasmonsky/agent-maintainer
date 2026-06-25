"""Tests for the quiet verifier orchestration."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from scripts import verify_quiet
from scripts.guardrail_config import GuardrailConfig
from scripts.guardrail_models import Check, CheckResult

CLI_COVERAGE_THRESHOLD = 92


def test_parse_csv_like_normalizes_repeated_values() -> None:
    assert verify_quiet.parse_csv_like(["src, tests", "tools/"]) == (
        "src",
        "tests",
        "tools",
    )
    assert verify_quiet.parse_csv_like(None) is None
    assert verify_quiet.parse_csv_like([" , "]) is None


def test_cli_overrides_replace_config_values() -> None:
    args = verify_quiet.parse_args(
        [
            "--source-root",
            "lib",
            "--test-root",
            "specs",
            "--coverage-fail-under",
            "92",
            "--enable-pip-audit",
        ]
    )

    config = verify_quiet.apply_cli_overrides(GuardrailConfig(), args)

    assert config.source_roots == ("lib",)
    assert config.test_roots == ("specs",)
    assert config.coverage_fail_under == CLI_COVERAGE_THRESHOLD
    assert config.enable_pip_audit is True


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
    results = [CheckResult("pip-audit", passed=True, output="disabled", skipped=True)]

    converted = verify_quiet.apply_optional_skip_policy(results, fail_on_optional_skip=True)

    assert converted == [
        CheckResult(
            "pip-audit",
            passed=False,
            output="optional check skipped: disabled",
            skipped=False,
        )
    ]


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
