"""Tests change-budget helper logic."""

from __future__ import annotations

import subprocess

import pytest

from guardrail_lib.checks import change_budget as check_change_budget
from scripts.guardrail_core.config import GuardrailConfig


def test_change_budget_classifies_python_source_and_tests() -> None:
    config = GuardrailConfig(source_roots=("scripts",), test_roots=("tests",))
    changes = [
        check_change_budget.FileChange("scripts/tool.py", 2, 1),
        check_change_budget.FileChange("scripts/package/__init__.py", 1, 0),
        check_change_budget.FileChange("tests/test_tool.py", 1, 0),
        check_change_budget.FileChange("README.md", 4, 0),
    ]

    source, tests = check_change_budget.changed_python_files(changes, config)

    assert [change.path for change in source] == ["scripts/tool.py"]
    assert [change.path for change in tests] == ["tests/test_tool.py"]
    assert check_change_budget.should_exclude("poetry.lock")
    assert check_change_budget.is_trivial_package_marker(
        check_change_budget.FileChange("scripts/package/__init__.py", 1, 0)
    )
    assert check_change_budget.diff_target_label("HEAD", staged=True) == "staged changes"


def test_change_budget_parse_csv_like_normalizes_values() -> None:
    assert check_change_budget.parse_csv_like(None) is None
    assert check_change_budget.parse_csv_like(["src, tests/", " scripts "]) == (
        "src",
        "tests",
        "scripts",
    )


def test_change_budget_reports_missing_tests_when_required() -> None:
    args = check_change_budget.parse_args([])
    config = GuardrailConfig(source_roots=("scripts",), test_roots=("tests",), require_tests=True)

    failures, warnings = check_change_budget.budget_messages(
        args,
        config,
        [check_change_budget.FileChange("scripts/tool.py", 1, 0)],
        [],
    )

    assert failures == []
    assert warnings == ["Python source changed, but no configured Python test files changed."]


def test_run_git_numstat_parses_output(monkeypatch: pytest.MonkeyPatch) -> None:
    completed = subprocess.CompletedProcess(
        ["git"],
        0,
        stdout="2\t3\tscripts/tool.py\n-\t-\timage.png\n",
        stderr="",
    )
    monkeypatch.setattr(check_change_budget.subprocess, "run", lambda *args, **_kwargs: completed)

    changes = check_change_budget.run_git_numstat("HEAD", staged=False)

    assert changes == [check_change_budget.FileChange("scripts/tool.py", 2, 3)]


def test_run_git_numstat_does_not_double_count_copied_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    numstat = subprocess.CompletedProcess(
        ["git"],
        0,
        stdout=(
            "0\t1\tscripts/check_tool.py => guardrail_lib/checks/tool.py\n"
            "5\t300\tscripts/check_tool.py\n"
        ),
        stderr="",
    )
    name_status = subprocess.CompletedProcess(
        ["git"],
        0,
        stdout="C099\tscripts/check_tool.py\tguardrail_lib/checks/tool.py\n",
        stderr="",
    )
    calls = [numstat, name_status]

    monkeypatch.setattr(
        check_change_budget.subprocess,
        "run",
        lambda *args, **_kwargs: calls.pop(0),
    )

    changes = check_change_budget.run_git_numstat("HEAD", staged=False)

    assert changes == [
        check_change_budget.FileChange(
            "scripts/check_tool.py => guardrail_lib/checks/tool.py",
            0,
            1,
        ),
        check_change_budget.FileChange("scripts/check_tool.py", 5, 0),
    ]


def test_change_budget_copied_source_paths_reports_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.CalledProcessError(1, ["git"], stderr="bad ref")

    monkeypatch.setattr(check_change_budget.subprocess, "run", fail_run)

    with pytest.raises(RuntimeError, match="staged changes: bad ref"):
        check_change_budget.copied_source_paths("HEAD", staged=True)


def test_change_budget_limit_helpers_report_warnings_and_blocks() -> None:
    args = check_change_budget.parse_args(
        ["--warn-lines", "1", "--block-lines", "3", "--warn-files", "1", "--block-files", "2"]
    )
    config = GuardrailConfig()
    changes = [
        check_change_budget.FileChange("scripts/a.py", 2, 0),
        check_change_budget.FileChange("scripts/b.py", 2, 0),
        check_change_budget.FileChange("scripts/c.py", 1, 0),
    ]
    warnings: list[str] = []

    line_failures = check_change_budget.line_budget_failures(args, config, changes, warnings)
    file_failures = check_change_budget.file_budget_failures(args, config, changes, warnings)

    assert line_failures == ["Python source diff is too large: 5 changed lines (block limit: 3)."]
    assert file_failures == ["Too many Python source files touched: 3 (block limit: 2)."]


def test_change_budget_limit_helpers_report_soft_warnings() -> None:
    args = check_change_budget.parse_args(
        ["--warn-lines", "1", "--block-lines", "10", "--warn-files", "1", "--block-files", "10"]
    )
    config = GuardrailConfig()
    changes = [
        check_change_budget.FileChange("scripts/a.py", 1, 1),
        check_change_budget.FileChange("scripts/b.py", 1, 0),
    ]
    warnings: list[str] = []

    assert check_change_budget.line_budget_failures(args, config, changes, warnings) == []
    assert check_change_budget.file_budget_failures(args, config, changes, warnings) == []
    assert warnings == [
        "Large Python source diff: 3 changed lines (warning threshold: 1).",
        "Many Python source files touched: 2 (warning threshold: 1).",
    ]


def test_change_budget_main_handles_runtime_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail_run(base_ref: str, *, staged: bool) -> list[check_change_budget.FileChange]:
        raise RuntimeError("git failed")

    monkeypatch.setattr(check_change_budget, "run_git_numstat", fail_run)

    assert check_change_budget.main([]) == 1
    assert "git failed" in capsys.readouterr().out


def test_change_budget_main_can_fail_warnings_as_errors(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        check_change_budget,
        "run_git_numstat",
        lambda base_ref, staged=False: [
            check_change_budget.FileChange("src/app.py", 1, 0),
        ],
    )
    monkeypatch.setattr(
        check_change_budget,
        "load_config",
        lambda: GuardrailConfig(source_roots=("src",), test_roots=("tests",), require_tests=True),
    )

    assert check_change_budget.main(["--warnings-as-errors"]) == 1
    assert "Change budget warnings" in capsys.readouterr().out


def test_change_budget_main_reports_failures(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        check_change_budget,
        "run_git_numstat",
        lambda base_ref, staged=False: [
            check_change_budget.FileChange("src/a.py", 4, 0),
        ],
    )
    monkeypatch.setattr(
        check_change_budget,
        "load_config",
        lambda: GuardrailConfig(
            source_roots=("src",),
            test_roots=("tests",),
            change_warn_lines=1,
            change_block_lines=2,
        ),
    )

    assert check_change_budget.main([]) == 1
    assert "Change budget failed" in capsys.readouterr().out


def test_change_budget_can_allow_source_changes_without_test_changes() -> None:
    args = check_change_budget.parse_args(["--allow-source-without-test-change"])
    config = GuardrailConfig(source_roots=("scripts",), test_roots=("tests",), require_tests=True)

    failures, warnings = check_change_budget.budget_messages(
        args,
        config,
        [check_change_budget.FileChange("scripts/tool.py", 1, 0)],
        [],
    )

    assert failures == []
    assert warnings == []


def test_change_budget_main_passes_clean_diff(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(check_change_budget, "run_git_numstat", lambda base_ref, staged=False: [])
    monkeypatch.setattr(check_change_budget, "load_config", GuardrailConfig)

    assert check_change_budget.main([]) == 0
