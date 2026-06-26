"""Tests for command execution and compact reporting helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.guardrail_core import executor as guardrail_executor
from scripts.guardrail_core import reporting as guardrail_reporting
from scripts.guardrail_models import Check, CheckResult


def test_run_check_prefers_structured_artifact_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = tmp_path / "logs" / "ruff.json"

    def fake_run(command: list[str]) -> tuple[int, str]:
        assert command == ["ruff"]
        artifact.write_text(
            """[
  {
    "code": "F401",
    "filename": "scripts/example.py",
    "location": {"row": 2, "column": 4},
    "message": "imported but unused"
  }
]""",
            encoding="utf-8",
        )
        return 1, "RAW OUTPUT SHOULD NOT BE USED\n"

    monkeypatch.setattr(guardrail_executor, "run_command", fake_run)

    result = guardrail_executor.run_check(
        Check("ruff", ["ruff"], frozenset(), artifact_paths=(str(artifact),)),
        tmp_path / "logs",
        3,
        200,
    )

    assert result.passed is False
    assert "scripts/example.py:2:4: F401: imported but unused" in result.output
    assert "RAW OUTPUT" not in result.output


def test_structured_artifact_summary_handles_pyright(tmp_path: Path) -> None:
    artifact = tmp_path / "pyright.json"
    artifact.write_text(
        """{
  "generalDiagnostics": [
    {
      "file": "scripts/example.py",
      "range": {"start": {"line": 1, "character": 3}},
      "severity": "error",
      "message": "Bad type",
      "rule": "reportAssignmentType"
    }
  ]
}""",
        encoding="utf-8",
    )

    summary = guardrail_reporting.structured_artifact_summary("pyright", (str(artifact),))

    assert summary == "scripts/example.py:2:4: error: Bad type [reportAssignmentType]"


def test_structured_artifact_summary_handles_bandit(tmp_path: Path) -> None:
    artifact = tmp_path / "bandit.json"
    artifact.write_text(
        """{
  "results": [
    {
      "filename": "scripts/example.py",
      "line_number": 10,
      "test_id": "B404",
      "issue_severity": "LOW",
      "issue_text": "subprocess import"
    }
  ]
}""",
        encoding="utf-8",
    )

    summary = guardrail_reporting.structured_artifact_summary("bandit", (str(artifact),))

    assert summary == "scripts/example.py:10: B404 LOW: subprocess import"


def test_structured_artifact_summary_falls_back_for_bad_artifacts(
    tmp_path: Path,
) -> None:
    bad_json = tmp_path / "ruff.json"
    bad_json.write_text("not json", encoding="utf-8")

    assert guardrail_reporting.structured_artifact_summary("unknown", ()) is None
    assert guardrail_reporting.structured_artifact_summary("ruff", ()) is None
    assert guardrail_reporting.structured_artifact_summary("ruff", (str(bad_json),)) is None
    assert guardrail_reporting.summarize_pyright_payload([]) is None
    assert guardrail_reporting.summarize_ruff_payload({}) is None
    assert guardrail_reporting.summarize_bandit_payload([]) is None
    assert guardrail_reporting.summarize_bandit_payload({"results": {}}) is None


def test_structured_payload_summaries_report_omitted_items() -> None:
    ruff_payload = [
        {
            "code": "F401",
            "filename": f"scripts/example_{index}.py",
            "location": {"row": 2, "column": 4},
            "message": "imported but unused",
        }
        for index in range(guardrail_reporting.STRUCTURED_DIAGNOSTIC_LIMIT + 1)
    ]
    bandit_payload = {
        "results": [
            {
                "filename": f"scripts/example_{index}.py",
                "line_number": 10,
                "test_id": "B404",
                "issue_severity": "LOW",
                "issue_text": "subprocess import",
            }
            for index in range(guardrail_reporting.STRUCTURED_DIAGNOSTIC_LIMIT + 1)
        ]
    }

    ruff_summary = guardrail_reporting.summarize_ruff_payload(ruff_payload)
    bandit_summary = guardrail_reporting.summarize_bandit_payload(bandit_payload)

    assert ruff_summary is not None
    assert bandit_summary is not None
    assert "more diagnostics omitted" in ruff_summary
    assert "more findings omitted" in bandit_summary


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
