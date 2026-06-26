"""Tests suppression-budget helper logic."""

from __future__ import annotations

import subprocess

import pytest

from ai_guardrails.checks import suppression_budget as check_suppression_budget
from ai_guardrails.core.config import GuardrailConfig

NOQA_SUPPRESSION = "# " + "noqa"
TYPE_IGNORE_SUPPRESSION = "# " + "type: ignore[assignment]"


def test_suppression_budget_detects_broad_suppressions() -> None:
    added = [
        ("scripts/tool.py", f"value = call()  {NOQA_SUPPRESSION}"),
        ("scripts/tool.py", f"other = call()  {TYPE_IGNORE_SUPPRESSION}"),
    ]

    failures = check_suppression_budget.suppression_failures(added, max_new_suppressions=1)

    assert any("broad noqa" in failure for failure in failures)
    assert any("Too many new suppression comments" in failure for failure in failures)


def test_suppression_added_python_lines_parses_diff(monkeypatch: pytest.MonkeyPatch) -> None:
    diff = f"+++ b/scripts/tool.py\n+value = call() {NOQA_SUPPRESSION}\n context\n"
    diff_result = subprocess.CompletedProcess(["git"], 0, stdout=diff, stderr="")
    name_status_result = subprocess.CompletedProcess(["git"], 0, stdout="", stderr="")
    calls = [diff_result, name_status_result]
    monkeypatch.setattr(
        check_suppression_budget.subprocess,
        "run",
        lambda *args, **_kwargs: calls.pop(0),
    )

    assert check_suppression_budget.added_python_lines("HEAD", staged=False) == [
        ("scripts/tool.py", f"value = call() {NOQA_SUPPRESSION}")
    ]


def test_suppression_added_python_lines_ignores_copied_destinations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    diff = f"+++ b/src/ai_guardrails/checks/tool.py\n+value = call() {NOQA_SUPPRESSION}\n"
    name_status = "C099\tscripts/check_tool.py\tsrc/ai_guardrails/checks/tool.py\n"
    diff_result = subprocess.CompletedProcess(["git"], 0, stdout=diff, stderr="")
    name_status_result = subprocess.CompletedProcess(
        ["git"],
        0,
        stdout=name_status,
        stderr="",
    )
    calls = [diff_result, name_status_result]
    monkeypatch.setattr(
        check_suppression_budget.subprocess,
        "run",
        lambda *args, **_kwargs: calls.pop(0),
    )

    assert check_suppression_budget.added_python_lines("HEAD", staged=False) == []


def test_suppression_copied_destination_paths_reports_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.CalledProcessError(1, ["git"], stderr="bad ref")

    monkeypatch.setattr(check_suppression_budget.subprocess, "run", fail_run)

    with pytest.raises(RuntimeError, match="staged changes: bad ref"):
        check_suppression_budget.copied_destination_paths("HEAD", staged=True)


def test_suppression_added_python_lines_skips_non_python_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    diff = (
        f"+++ b/README.md\n+text {NOQA_SUPPRESSION}\n"
        f"+++ b/scripts/tool.py\n+value = call() {NOQA_SUPPRESSION}\n"
    )
    diff_result = subprocess.CompletedProcess(["git"], 0, stdout=diff, stderr="")
    name_status_result = subprocess.CompletedProcess(["git"], 0, stdout="", stderr="")
    calls = [diff_result, name_status_result]
    monkeypatch.setattr(
        check_suppression_budget.subprocess,
        "run",
        lambda *args, **_kwargs: calls.pop(0),
    )

    assert check_suppression_budget.added_python_lines("HEAD", staged=False) == [
        ("scripts/tool.py", f"value = call() {NOQA_SUPPRESSION}")
    ]


def test_suppression_classifies_broad_type_ignore() -> None:
    issues = check_suppression_budget.classify("pkg/a.py", "value = call() # type: ignore")

    assert [issue.reason for issue in issues] == ["broad type ignore without specific error code"]


def test_suppression_main_reports_failures(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        check_suppression_budget,
        "added_python_lines",
        lambda base_ref, staged=False: [
            ("scripts/tool.py", f"value = call() {NOQA_SUPPRESSION}"),
        ],
    )
    monkeypatch.setattr(
        check_suppression_budget,
        "load_config",
        lambda: GuardrailConfig(suppression_max_new=0),
    )

    assert check_suppression_budget.main([]) == 1
    assert "Suppression budget failed" in capsys.readouterr().out


def test_suppression_main_passes_without_new_suppressions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        check_suppression_budget, "added_python_lines", lambda *_args, **_kwargs: []
    )
    monkeypatch.setattr(check_suppression_budget, "load_config", GuardrailConfig)

    assert check_suppression_budget.main([]) == 0


def test_suppression_main_handles_runtime_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail_added(base_ref: str, *, staged: bool) -> list[tuple[str, str]]:
        raise RuntimeError("diff failed")

    monkeypatch.setattr(check_suppression_budget, "added_python_lines", fail_added)

    assert check_suppression_budget.main([]) == 1
    assert "diff failed" in capsys.readouterr().out
