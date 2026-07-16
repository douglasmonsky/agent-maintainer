"""Tests bounded Checkstyle XML parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer.ecosystems.java.reports.checkstyle import parse_checkstyle_report
from agent_maintainer.ecosystems.java.reports.xml import (
    MAX_REPAIR_TEXT_CHARS,
    JavaXmlError,
    XmlLimits,
)

TEXT_ENCODING = "utf-8"
FIRST_FINDING_LINE = 7


def test_parser_normalizes_warnings_errors_and_absolute_paths(tmp_path: Path) -> None:
    """Standard Checkstyle findings become repository-relative repair facts."""
    source = tmp_path / "app" / "src" / "main" / "java" / "example" / "App.java"
    payload = f"""<checkstyle version="10.17">
      <file name="{source}">
        <error line="7" column="12" severity="warning"
          message="Avoid inline conditionals"
          source="com.puppycrawl.tools.checkstyle.checks.coding.AvoidInlineConditionalsCheck"/>
        <error line="9" severity="error" message="Name must match"
          source="com.acme.NamingCheck"/>
      </file>
    </checkstyle>"""

    report = parse_checkstyle_report(write_xml(tmp_path, payload), gradle_root=tmp_path)

    assert [finding.rule for finding in report.findings] == [
        "AvoidInlineConditionals",
        "Naming",
    ]
    assert [finding.severity for finding in report.findings] == ["warning", "error"]
    assert report.findings[0].path == "app/src/main/java/example/App.java"
    assert report.findings[0].line == FIRST_FINDING_LINE


def test_parser_accepts_absent_optional_fields_and_truncates_messages(
    tmp_path: Path,
) -> None:
    """Optional location metadata is not required and long details are bounded."""
    payload = """<checkstyle><file name="src/App.java">
      <error message="{}"/>
    </file></checkstyle>""".format("x" * 700)

    report = parse_checkstyle_report(write_xml(tmp_path, payload), gradle_root=tmp_path)

    finding = report.findings[0]
    assert finding.rule == "checkstyle"
    assert finding.subject == "checkstyle"
    assert finding.line is None
    assert finding.message.endswith("...")
    assert len(finding.message) == MAX_REPAIR_TEXT_CHARS


@pytest.mark.parametrize(
    ("payload", "message"),
    (
        ("<checkstyle>", "malformed"),
        ("<not-checkstyle/>", "root"),
        ("<checkstyle><exception>boom</exception></checkstyle>", "incomplete"),
        ("<checkstyle><file><error message='bad'/></file></checkstyle>", "file name"),
        (
            "<checkstyle><file name='App.java'><error line='zero' message='bad'/>"
            "</file></checkstyle>",
            "line",
        ),
        (
            "<checkstyle><file name='../escape.java'><error message='bad'/></file></checkstyle>",
            "repository-relative",
        ),
        (
            "<checkstyle><file name='/etc/passwd'><error message='bad'/></file></checkstyle>",
            "escapes Gradle root",
        ),
        (
            '<!DOCTYPE checkstyle SYSTEM "file:///etc/passwd"><checkstyle/>',
            "DTD or entity",
        ),
    ),
)
def test_parser_rejects_unsafe_or_incomplete_reports(
    tmp_path: Path,
    payload: str,
    message: str,
) -> None:
    """Unsafe, malformed, and incomplete Checkstyle evidence fails closed."""
    with pytest.raises(JavaXmlError, match=message):
        parse_checkstyle_report(write_xml(tmp_path, payload), gradle_root=tmp_path)


def test_parser_rejects_oversized_input(tmp_path: Path) -> None:
    """The shared byte boundary applies to Checkstyle reports."""
    report = write_xml(tmp_path, "<checkstyle/>" + (" " * 32))

    with pytest.raises(JavaXmlError, match="byte limit"):
        parse_checkstyle_report(
            report,
            gradle_root=tmp_path,
            limits=XmlLimits(max_bytes=16),
        )


def write_xml(root: Path, payload: str) -> Path:
    """Write one Checkstyle report fixture."""
    report = root / "checkstyle.xml"
    report.write_text(payload, encoding=TEXT_ENCODING)
    return report
