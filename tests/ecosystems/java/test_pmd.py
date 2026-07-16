"""Tests bounded PMD XML parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer.ecosystems.java.reports.pmd import parse_pmd_report
from agent_maintainer.ecosystems.java.reports.xml import MAX_REPAIR_TEXT_CHARS, JavaXmlError

TEXT_ENCODING = "utf-8"
COMPLEXITY_METRIC = 12
COMPLEXITY_LINE = 11


def test_parser_normalizes_namespaced_findings_and_complexity(tmp_path: Path) -> None:
    """PMD dialect metadata becomes semantic findings and numeric ceilings."""
    payload = """<pmd xmlns="https://pmd-code.org/schema/report/2.0.0" version="7.4.0">
      <file name="src/main/java/example/App.java">
        <violation beginline="11" endline="18" rule="CyclomaticComplexity"
          ruleset="Design" priority="2" class="App" method="run">
          The method 'run' has a cyclomatic complexity of 12.
        </violation>
        <violation beginline="22" rule="UnusedLocalVariable" priority="4">
          Avoid unused local variables
        </violation>
      </file>
    </pmd>"""

    report = parse_pmd_report(write_xml(tmp_path, payload), gradle_root=tmp_path)

    complexity, unused = report.findings
    assert complexity.subject == "App#run"
    assert complexity.metric == COMPLEXITY_METRIC
    assert complexity.severity == "error"
    assert complexity.line == COMPLEXITY_LINE
    assert unused.subject == "UnusedLocalVariable"
    assert unused.severity == "info"


def test_parser_accepts_absent_optional_metadata_and_truncates(tmp_path: Path) -> None:
    """PMD class, method, line, priority, and message metadata are optional."""
    payload = """<pmd><file name="src/App.java">
      <violation rule="RuleOne">{}</violation>
    </file></pmd>""".format("detail " * 100)

    report = parse_pmd_report(write_xml(tmp_path, payload), gradle_root=tmp_path)

    finding = report.findings[0]
    assert finding.subject == "RuleOne"
    assert finding.line is None
    assert finding.severity == "warning"
    assert finding.message.endswith("...")
    assert len(finding.message) == MAX_REPAIR_TEXT_CHARS


def test_parser_keeps_complexity_metric_beyond_published_message_limit(
    tmp_path: Path,
) -> None:
    """Truncating repair text does not discard a numeric ratchet measurement."""
    payload = """<pmd><file name="src/App.java">
      <violation rule="CyclomaticComplexity">{} complexity of 12</violation>
    </file></pmd>""".format("detail " * 100)

    finding = parse_pmd_report(write_xml(tmp_path, payload), gradle_root=tmp_path).findings[0]

    assert finding.metric == COMPLEXITY_METRIC
    assert len(finding.message) == MAX_REPAIR_TEXT_CHARS


@pytest.mark.parametrize(
    ("payload", "message"),
    (
        ("<pmd>", "malformed"),
        ("<not-pmd/>", "root"),
        ("<pmd><error filename='App.java' msg='analysis failed'/></pmd>", "incomplete"),
        ("<pmd><file><violation rule='A'>bad</violation></file></pmd>", "file name"),
        ("<pmd><file name='App.java'><violation>bad</violation></file></pmd>", "rule"),
        (
            "<pmd><file name='App.java'><violation rule='A' priority='9'>bad"
            "</violation></file></pmd>",
            "priority",
        ),
        (
            "<pmd><file name='App.java'><violation rule='A' beginline='zero'>bad"
            "</violation></file></pmd>",
            "line",
        ),
        (
            "<!DOCTYPE pmd [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]><pmd>&xxe;</pmd>",
            "DTD or entity",
        ),
    ),
)
def test_parser_rejects_unsafe_or_incomplete_reports(
    tmp_path: Path,
    payload: str,
    message: str,
) -> None:
    """Unsafe, malformed, and incomplete PMD evidence fails closed."""
    with pytest.raises(JavaXmlError, match=message):
        parse_pmd_report(write_xml(tmp_path, payload), gradle_root=tmp_path)


def write_xml(root: Path, payload: str) -> Path:
    """Write one PMD report fixture."""
    report = root / "pmd.xml"
    report.write_text(payload, encoding=TEXT_ENCODING)
    return report
