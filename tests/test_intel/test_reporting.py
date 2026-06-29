"""Tests test-intelligence report rendering."""

from __future__ import annotations

import json
from pathlib import Path

from agent_maintainer.test_intel.coverage import coverage_for_changed_sources
from agent_maintainer.test_intel.models import CoverageSummary, TestIntelReport, TestMatch
from agent_maintainer.test_intel.reporting import render_json, render_text, suggested_actions

JSON_COVERAGE_PERCENT = 87.5
XML_COVERAGE_PERCENT = 75.0


def test_render_text_includes_reasons_and_commands() -> None:
    """Text output includes ranked evidence and focused commands."""

    report = sample_report()

    output = render_text(report)

    assert "Test intelligence changed source" in output
    assert "src/pkg/widget.py" in output
    assert "tests/test_widget.py" in output
    assert "confidence: high" in output
    assert "naming match" in output
    assert "Run: python -m pytest tests/test_widget.py -q" in output


def test_render_json_is_stable() -> None:
    """JSON output contains stable top-level keys."""

    payload = json.loads(render_json(sample_report()))

    assert payload == {
        "changed_source": ["src/pkg/widget.py"],
        "coverage": {
            "branch_coverage_gaps": None,
            "changed_line_coverage": 92.5,
        },
        "likely_tests": [
            {
                "confidence": "high",
                "pytest_command": "python -m pytest tests/test_widget.py -q",
                "reasons": ["naming match", "imports changed module"],
                "source_path": "src/pkg/widget.py",
                "test_path": "tests/test_widget.py",
            }
        ],
        "suggested_actions": ["Run: python -m pytest tests/test_widget.py -q"],
    }


def test_coverage_json_reports_changed_file_percent(tmp_path: Path) -> None:
    """Coverage JSON provides changed-line coverage when present."""

    (tmp_path / "coverage.json").write_text(
        json.dumps(
            {
                "files": {
                    "src/pkg/widget.py": {
                        "summary": {
                            "percent_covered": JSON_COVERAGE_PERCENT,
                        },
                    },
                },
            },
        ),
        encoding="utf-8",
    )

    coverage = coverage_for_changed_sources(tmp_path, ("src/pkg/widget.py",))

    assert coverage.changed_line_coverage == JSON_COVERAGE_PERCENT


def test_coverage_xml_reports_changed_file_percent(tmp_path: Path) -> None:
    """Coverage XML provides changed-line coverage when JSON is absent."""

    (tmp_path / "coverage.xml").write_text(
        """
<coverage>
  <packages>
    <package>
      <classes>
        <class filename="src/pkg/widget.py" line-rate="0.75" />
      </classes>
    </package>
  </packages>
</coverage>
""".lstrip(),
        encoding="utf-8",
    )

    coverage = coverage_for_changed_sources(tmp_path, ("src/pkg/widget.py",))

    assert coverage.changed_line_coverage == XML_COVERAGE_PERCENT


def sample_report() -> TestIntelReport:
    """Return report fixture."""

    match = TestMatch(
        source_path="src/pkg/widget.py",
        test_path="tests/test_widget.py",
        confidence="high",
        reasons=("naming match", "imports changed module"),
    )
    return TestIntelReport(
        changed_source=("src/pkg/widget.py",),
        likely_tests=(match,),
        coverage=CoverageSummary(changed_line_coverage=92.5),
        suggested_actions=suggested_actions((match,)),
    )
