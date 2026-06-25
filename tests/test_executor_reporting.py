"""Tests for command execution and compact reporting helpers."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from scripts import guardrail_executor, guardrail_reporting
from scripts.guardrail_models import Check, CheckResult


def test_tool_search_path_prefers_local_virtualenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    monkeypatch.setenv("PATH", "/usr/bin")

    search_path = guardrail_executor.tool_search_path().split(os.pathsep)

    assert search_path[0] == ".venv/bin"
    assert "/usr/bin" in search_path


def test_missing_requirement_reports_required_path(tmp_path: Path) -> None:
    check = Check("missing", ["true"], frozenset(), required_paths=("missing.py",))

    assert guardrail_executor.missing_requirement(check) == "required path 'missing.py' is absent"


def test_optional_skip_reports_configured_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    check = Check(
        "import-linter",
        ["lint-imports"],
        frozenset(),
        optional_skip_reason=".importlinter is absent",
    )

    assert guardrail_executor.missing_requirement(check) == (
        "optional skip: .importlinter is absent"
    )


def test_run_check_writes_skip_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    check = Check("pip-audit", ["pip-audit"], frozenset(), optional_skip_reason="disabled")

    result = guardrail_executor.run_check(check, tmp_path / "logs", 5, 200)

    assert result == CheckResult("pip-audit", passed=True, output="disabled", skipped=True)
    assert (tmp_path / "logs" / "pip-audit.log").read_text(encoding="utf-8")


def test_run_check_summarizes_command_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(command: list[str]) -> tuple[int, str]:
        assert command == ["tool"]
        return 1, "\n".join(f"line {index}" for index in range(10))

    monkeypatch.setattr(guardrail_executor, "run_command", fake_run)

    result = guardrail_executor.run_check(
        Check("tool", ["tool"], frozenset()), tmp_path / "logs", 3, 200
    )

    assert result.passed is False
    assert "line 0" in result.output
    assert "more lines omitted" in result.output


def test_reporting_truncates_lines_and_characters() -> None:
    assert guardrail_reporting.nonblank_lines("a\n\n b ") == ["a", " b"]
    assert guardrail_reporting.truncate_lines(["a", "b", "c"], 2)[-1].startswith("... 1")
    assert guardrail_reporting.truncate_chars("abcdef", 3).startswith("abc")
    assert guardrail_reporting.compact_output("", 2, 5) == "(no output)"


def test_pyright_summary_formats_diagnostics() -> None:
    raw = """
{
  "generalDiagnostics": [
    {
      "file": "scripts/example.py",
      "severity": "error",
      "message": "Bad type",
      "rule": "reportAssignmentType",
      "range": {"start": {"line": 2, "character": 4}}
    }
  ]
}
""".strip()

    summary = guardrail_reporting.summarize_pyright(raw)

    assert summary == ("scripts/example.py:3:5: error: Bad type [reportAssignmentType]")


def test_print_success_and_failures(capsys: pytest.CaptureFixture[str]) -> None:
    skipped = [CheckResult("optional", passed=True, output="not configured", skipped=True)]
    guardrail_reporting.print_success(skipped)
    assert "SKIPPED optional checks" in capsys.readouterr().out

    guardrail_reporting.print_failures(
        "full",
        [CheckResult("ruff", passed=False, output="lint failed")],
        skipped,
    )
    output = capsys.readouterr().out
    assert "FAIL: 1 check(s) failed [full]" in output
    assert "lint failed" in output
