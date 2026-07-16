"""Tests bounded SpotBugs XML parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer.ecosystems.java.reports.spotbugs import parse_spotbugs_report
from agent_maintainer.ecosystems.java.reports.xml import JavaXmlError, XmlLimits

TEXT_ENCODING = "utf-8"
TINY_BYTE_LIMIT = 16
VALID_REPORT = """<?xml version="1.0" encoding="UTF-8"?>
<BugCollection>
  <Project projectName="demo"/>
  <BugInstance type="NP_NULL_ON_SOME_PATH">
    <Class classname="example.App"/>
    <Method classname="example.App" name="run" signature="()V"/>
    <LongMessage>Possible null value</LongMessage>
  </BugInstance>
  <Errors errors="0" missingClasses="0"/>
</BugCollection>
"""


def test_parser_extracts_native_filter_identity(tmp_path: Path) -> None:
    """A valid report yields bounded SpotBugs native-filter identities."""
    report = write_xml(tmp_path, VALID_REPORT)

    parsed = parse_spotbugs_report(report)

    assert len(parsed.findings) == 1
    assert parsed.findings[0].bug_type == "NP_NULL_ON_SOME_PATH"
    assert parsed.findings[0].class_name == "example.App"
    assert parsed.findings[0].method_name == "run"


@pytest.mark.parametrize(
    "payload",
    (
        '<!DOCTYPE foo SYSTEM "file:///etc/passwd"><BugCollection/>',
        '<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
        "<BugCollection>&xxe;</BugCollection>",
    ),
)
def test_parser_rejects_dtd_and_entities(tmp_path: Path, payload: str) -> None:
    """DTD and entity declarations are rejected before XML parsing."""
    report = write_xml(tmp_path, payload)

    with pytest.raises(JavaXmlError, match="DTD or entity"):
        parse_spotbugs_report(report)


@pytest.mark.parametrize(
    ("limits", "payload", "message"),
    (
        (XmlLimits(max_bytes=TINY_BYTE_LIMIT), VALID_REPORT, "byte limit"),
        (XmlLimits(max_elements=2), "<BugCollection><A/><B/></BugCollection>", "element limit"),
        (
            XmlLimits(max_findings=1),
            "<BugCollection><BugInstance type='A'><Class classname='A'/></BugInstance>"
            "<BugInstance type='B'><Class classname='B'/></BugInstance></BugCollection>",
            "finding limit",
        ),
        (
            XmlLimits(max_message_chars=4),
            "<BugCollection><BugInstance type='A'><Class classname='A'/>"
            "<LongMessage>too long</LongMessage></BugInstance></BugCollection>",
            "message limit",
        ),
    ),
)
def test_parser_enforces_resource_limits(
    tmp_path: Path,
    limits: XmlLimits,
    payload: str,
    message: str,
) -> None:
    """Every parser resource boundary fails closed."""
    report = write_xml(tmp_path, payload)

    with pytest.raises(JavaXmlError, match=message):
        parse_spotbugs_report(report, limits=limits)


@pytest.mark.parametrize(
    ("payload", "message"),
    (
        ("<BugCollection>", "malformed"),
        ("<NotSpotBugs/>", "root"),
        (
            "<BugCollection><BugInstance><Class classname='A'/></BugInstance></BugCollection>",
            "missing type",
        ),
        (
            "<BugCollection><Errors errors='1' missingClasses='0'/></BugCollection>",
            "incomplete",
        ),
    ),
)
def test_parser_rejects_malformed_or_incomplete(
    tmp_path: Path,
    payload: str,
    message: str,
) -> None:
    """Malformed schemas and incomplete analysis evidence are refused."""
    report = write_xml(tmp_path, payload)

    with pytest.raises(JavaXmlError, match=message):
        parse_spotbugs_report(report)


def write_xml(root: Path, payload: str) -> Path:
    """Write one report fixture."""
    report = root / "spotbugs.xml"
    report.write_text(payload, encoding=TEXT_ENCODING)
    return report
