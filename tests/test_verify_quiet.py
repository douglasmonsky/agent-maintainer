"""Tests for the quiet verifier orchestration."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ai_guardrails.core.config import GuardrailConfig
from ai_guardrails.models import Check, CheckResult
from ai_guardrails.verify import quiet as verify_quiet

CLI_COVERAGE_THRESHOLD = 92
CLI_INTERROGATE_THRESHOLD = 30
STRICT_COMPLEXITY = 8


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
