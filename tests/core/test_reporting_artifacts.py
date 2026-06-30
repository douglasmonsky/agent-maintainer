"""Tests for command execution and compact reporting helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer.core import executor as maintainer_executor
from agent_maintainer.core import reporting as maintainer_reporting
from agent_maintainer.models import Check, CheckResult


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

    monkeypatch.setattr(maintainer_executor, "run_command", fake_run)

    result = maintainer_executor.run_check(
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

    summary = maintainer_reporting.structured_artifact_summary("pyright", (str(artifact),))

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

    summary = maintainer_reporting.structured_artifact_summary("bandit", (str(artifact),))

    assert summary == "scripts/example.py:10: B404 LOW: subprocess import"


def test_structured_artifact_summary_falls_back_for_bad_artifacts(
    tmp_path: Path,
) -> None:
    bad_json = tmp_path / "ruff.json"
    bad_json.write_text("not json", encoding="utf-8")

    assert maintainer_reporting.structured_artifact_summary("unknown", ()) is None
    assert maintainer_reporting.structured_artifact_summary("ruff", ()) is None
    assert maintainer_reporting.structured_artifact_summary("ruff", (str(bad_json),)) is None
    assert maintainer_reporting.summarize_pyright_payload([]) is None
    assert maintainer_reporting.summarize_ruff_payload({}) is None
    assert maintainer_reporting.summarize_bandit_payload([]) is None
    assert maintainer_reporting.summarize_bandit_payload({"results": {}}) is None


def test_structured_payload_summaries_report_omitted_items() -> None:
    ruff_payload = [
        {
            "code": "F401",
            "filename": f"scripts/example_{index}.py",
            "location": {"row": 2, "column": 4},
            "message": "imported but unused",
        }
        for index in range(maintainer_reporting.STRUCTURED_DIAGNOSTIC_LIMIT + 1)
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
            for index in range(maintainer_reporting.STRUCTURED_DIAGNOSTIC_LIMIT + 1)
        ]
    }

    ruff_summary = maintainer_reporting.summarize_ruff_payload(ruff_payload)
    bandit_summary = maintainer_reporting.summarize_bandit_payload(bandit_payload)

    assert ruff_summary is not None
    assert bandit_summary is not None
    assert "more diagnostics omitted" in ruff_summary
    assert "more findings omitted" in bandit_summary


def test_reporting_truncates_lines_and_characters() -> None:
    assert maintainer_reporting.nonblank_lines("a\n\n b ") == ["a", " b"]
    assert maintainer_reporting.truncate_lines(["a", "b", "c"], 2)[-1].startswith("... 1")
    assert maintainer_reporting.truncate_chars("abcdef", 3).startswith("abc")
    assert maintainer_reporting.compact_output("", 2, 5) == "(no output)"
    assert maintainer_reporting.compact_output("alpha\nbeta", 10, 200) == "alpha\nbeta"


def test_diagnostic_formatters_preserve_defaults() -> None:
    assert maintainer_reporting.format_diagnostic({}) == "<unknown>:1:1: error: "
    assert maintainer_reporting.format_diagnostic({"range": "bad"}) == "<unknown>:1:1: error: "
    assert maintainer_reporting.format_ruff_diagnostic({}) == "<unknown>:1:1: ruff: "
    assert maintainer_reporting.format_bandit_finding({}) == "<unknown>:1: bandit UNKNOWN: "


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

    summary = maintainer_reporting.summarize_pyright(raw)

    assert summary == ("scripts/example.py:3:5: error: Bad type [reportAssignmentType]")


def test_pyright_summary_reports_single_omitted_diagnostic() -> None:
    payload = {
        "generalDiagnostics": [
            {
                "file": f"scripts/example_{index}.py",
                "range": {"start": {"line": index, "character": 0}},
                "severity": "error",
                "message": "Bad type",
            }
            for index in range(maintainer_reporting.PYRIGHT_DIAGNOSTIC_LIMIT + 1)
        ]
    }

    summary = maintainer_reporting.summarize_pyright_payload(payload)

    assert summary is not None
    assert "... 1 more diagnostics omitted. See .verify-logs/pyright.log" in summary


def test_summarize_check_only_applies_pyright_parser_to_pyright() -> None:
    raw = """{"generalDiagnostics":[{"file":"x.py","message":"Bad type"}]}"""

    non_pyright_summary = maintainer_reporting.summarize_check("tool", raw, 5, 500)
    pyright_summary = maintainer_reporting.summarize_check("pyright", raw, 5, 500)

    assert non_pyright_summary == raw
    assert pyright_summary == "x.py:1:1: error: Bad type"


def test_artifact_fallback_preserves_check_specific_summary() -> None:
    raw = """{"generalDiagnostics":[{"file":"x.py","message":"Bad type"}]}"""

    assert (
        maintainer_reporting.summarize_check_from_artifacts(
            "pyright",
            (),
            raw,
            5,
            500,
        )
        == "x.py:1:1: error: Bad type"
    )


def test_print_success_and_failures(capsys: pytest.CaptureFixture[str]) -> None:
    skipped = [CheckResult("optional", passed=True, output="not configured", skipped=True)]
    maintainer_reporting.print_success(
        skipped,
        run_details=("Profile: full", "Run ID: 20260625T100000Z-full-test"),
    )
    success_output = capsys.readouterr().out
    assert "Profile: full" in success_output
    assert "Run ID: 20260625T100000Z-full-test" in success_output
    assert "SKIPPED optional checks" in success_output

    maintainer_reporting.print_failures(
        "full",
        [CheckResult("ruff", passed=False, output="lint failed")],
        skipped,
        run_details=("Run ID: 20260625T100000Z-full-test", "Duration: 1.0s"),
    )
    output = capsys.readouterr().out
    assert "FAIL: 1 check(s) failed [full]" in output
    assert "Run ID: 20260625T100000Z-full-test" in output
    assert "Duration: 1.0s" in output
    assert "Failed checks: ruff" in output
    assert "lint failed" in output
    assert (
        "Smallest rerun after fixes: `python3 -m agent_maintainer verify --profile full`"
    ) in output


def test_print_success_exact_sections(capsys: pytest.CaptureFixture[str]) -> None:
    skipped = [CheckResult("optional", passed=True, output="not configured", skipped=True)]
    warnings = [CheckResult("change-budget", passed=True, output="warning")]

    maintainer_reporting.print_success(
        skipped,
        warnings,
        run_details=("Profile: full", "Run ID: 20260625T100000Z-full-test"),
    )

    assert capsys.readouterr().out.splitlines() == [
        "PASS",
        "Profile: full",
        "Run ID: 20260625T100000Z-full-test",
        "WARNINGS:",
        "  change-budget: warning",
        "SKIPPED optional checks:",
        "  optional: not configured",
    ]


def test_print_failures_includes_context_and_footer(capsys: pytest.CaptureFixture[str]) -> None:
    skipped = [CheckResult("optional", passed=True, output="not configured", skipped=True)]

    maintainer_reporting.print_failures(
        "full",
        [
            CheckResult("ruff", passed=False, output="lint failed"),
            CheckResult("pyright", passed=False, output="type failed"),
        ],
        skipped,
        run_details=("Run ID: 20260625T100000Z-full-test", "Duration: 1.0s"),
        footer=(
            ".verify-logs/runs/20260625T100000Z-full-test",
            "python3 -m agent_maintainer verify --profile full",
        ),
    )

    output = capsys.readouterr().out
    assert "FAIL: 2 check(s) failed [full]" in output
    assert "Failed checks: ruff, pyright" in output
    assert "1. ruff\nlint failed\nNext context:" in output
    assert "2. pyright\ntype failed\nNext context:" in output
    assert (
        "python -m agent_maintainer context --log-dir "
        ".verify-logs/runs/20260625T100000Z-full-test failures --check ruff --limit 20"
    ) in output
    assert "Full logs are in .verify-logs/runs/20260625T100000Z-full-test." in output
    assert (
        "Smallest rerun after fixes: `python3 -m agent_maintainer verify --profile full`"
    ) in output
