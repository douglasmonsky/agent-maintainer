"""Tests test-intelligence report rendering."""

from __future__ import annotations

import json
from pathlib import Path

from agent_maintainer.test_intel import coverage_lines
from agent_maintainer.test_intel.coverage import (
    coverage_for_changed_sources,
    coverage_from_json,
    coverage_from_xml,
)
from agent_maintainer.test_intel.models import CoverageSummary, TestIntelReport, TestMatch
from agent_maintainer.test_intel.reporting import render_json, render_text, suggested_actions

JSON_COVERAGE_PERCENT = 87.5
XML_COVERAGE_PERCENT = 75.0
CHANGED_LINE_PERCENT = 50.0


def test_parse_changed_lines_reads_new_file_hunks() -> None:
    """Unified diff parsing returns changed new-file line numbers."""
    diff_text = """\
diff --git a/src/pkg/widget.py b/src/pkg/widget.py
--- a/src/pkg/widget.py
+++ b/src/pkg/widget.py
@@ -8,0 +9,2 @@
+covered()
+missing()
@@ -20 +22 @@
-old()
+new()
"""

    changed_lines = coverage_lines.parse_changed_lines(
        diff_text,
        frozenset(("src/pkg/widget.py",)),
    )

    assert changed_lines == {"src/pkg/widget.py": frozenset((9, 10, 22))}


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
            "changed_source_file_coverage": 88.0,
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
    """Coverage JSON provides changed source-file coverage."""

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

    assert coverage.changed_source_file_coverage == JSON_COVERAGE_PERCENT
    assert coverage.changed_line_coverage is None


def test_coverage_json_reports_changed_line_percent(tmp_path: Path) -> None:
    """Coverage JSON provides changed-line coverage for executable diff lines."""
    coverage_path = tmp_path / "coverage.json"
    coverage_path.write_text(
        json.dumps(
            {
                "files": {
                    "src/pkg/widget.py": {
                        "executed_lines": [10],
                        "missing_lines": [11],
                        "summary": {
                            "percent_covered": JSON_COVERAGE_PERCENT,
                        },
                    },
                },
            },
        ),
        encoding="utf-8",
    )

    coverage = coverage_from_json(
        coverage_path,
        ("src/pkg/widget.py",),
        {"src/pkg/widget.py": frozenset((10, 11, 12))},
    )

    assert coverage.changed_source_file_coverage == JSON_COVERAGE_PERCENT
    assert coverage.changed_line_coverage == CHANGED_LINE_PERCENT


def test_coverage_xml_reports_changed_file_percent(tmp_path: Path) -> None:
    """Coverage XML provides changed source-file coverage when JSON is absent."""

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

    assert coverage.changed_source_file_coverage == XML_COVERAGE_PERCENT
    assert coverage.changed_line_coverage is None


def test_coverage_xml_reports_changed_line_percent(tmp_path: Path) -> None:
    """Coverage XML provides changed-line coverage for executable diff lines."""
    coverage_path = tmp_path / "coverage.xml"
    coverage_path.write_text(
        """
<coverage>
  <packages>
    <package>
      <classes>
        <class filename="src/pkg/widget.py" line-rate="0.75">
          <lines>
            <line number="10" hits="1" />
            <line number="11" hits="0" />
          </lines>
        </class>
      </classes>
    </package>
  </packages>
</coverage>
""".lstrip(),
        encoding="utf-8",
    )

    coverage = coverage_from_xml(
        coverage_path,
        ("src/pkg/widget.py",),
        {"src/pkg/widget.py": frozenset((10, 11, 12))},
    )

    assert coverage.changed_source_file_coverage == XML_COVERAGE_PERCENT
    assert coverage.changed_line_coverage == CHANGED_LINE_PERCENT


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
        coverage=CoverageSummary(
            changed_source_file_coverage=88.0,
            changed_line_coverage=92.5,
        ),
        suggested_actions=suggested_actions((match,)),
    )
