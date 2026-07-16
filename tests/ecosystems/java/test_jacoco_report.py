"""Tests exact bounded JaCoCo report parsing."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from agent_maintainer.ecosystems.java.reports import jacoco
from agent_maintainer.ecosystems.java.reports.xml import DEFAULT_MAX_XML_BYTES, JavaXmlError

EXPECTED_COVERED_LINES = 3


def test_parses_report_level_line_and_branch_counters_exactly(tmp_path: Path) -> None:
    report = write_report(
        tmp_path,
        """<report name="example">
        <counter type="LINE" missed="1" covered="3"/>
        <counter type="BRANCH" missed="1" covered="2"/>
        </report>""",
    )

    coverage = jacoco.parse_jacoco_report(report)

    assert coverage.line.missed == 1
    assert coverage.line.covered == EXPECTED_COVERED_LINES
    assert coverage.line.percentage == Decimal("75.0000")
    assert coverage.branch.percentage == Decimal("66.6667")


def test_zero_denominator_is_zero_coverage(tmp_path: Path) -> None:
    report = write_report(
        tmp_path,
        """<report name="empty">
        <counter type="LINE" missed="0" covered="0"/>
        <counter type="BRANCH" missed="0" covered="0"/>
        </report>""",
    )

    coverage = jacoco.parse_jacoco_report(report)

    assert coverage.line.percentage == Decimal("0.0000")
    assert coverage.branch.percentage == Decimal("0.0000")


@pytest.mark.parametrize(
    "payload",
    (
        "<report>",
        '<report><counter type="LINE" missed="x" covered="1"/></report>',
        '<report><counter type="LINE" missed="0" covered="1"/></report>',
        "<!DOCTYPE report [<!ENTITY x SYSTEM 'file:///etc/passwd'>]><report/>",
    ),
)
def test_rejects_malformed_incomplete_or_unsafe_reports(tmp_path: Path, payload: str) -> None:
    report = write_report(tmp_path, payload)

    with pytest.raises(JavaXmlError):
        jacoco.parse_jacoco_report(report)


def test_rejects_oversized_report(tmp_path: Path) -> None:
    report = tmp_path / "jacoco.xml"
    report.write_bytes(b"<report>" + b" " * DEFAULT_MAX_XML_BYTES + b"</report>")

    with pytest.raises(JavaXmlError, match="byte limit"):
        jacoco.parse_jacoco_report(report)


def write_report(tmp_path: Path, payload: str) -> Path:
    report = tmp_path / "jacoco.xml"
    report.write_text(payload, encoding="utf-8")
    return report
