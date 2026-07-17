"""Tests bounded JUnit XML parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer.ecosystems.java.reports.junit import parse_junit_report
from agent_maintainer.ecosystems.java.reports.xml import (
    MAX_REPAIR_TEXT_CHARS,
    JavaXmlError,
    XmlLimits,
)

TEXT_ENCODING = "utf-8"


def test_parser_aggregates_modules_failures_errors_and_skips(tmp_path: Path) -> None:
    """Nested module suites yield exact totals and bounded problem facts."""
    payload = """<testsuites tests="3" failures="1" errors="1" skipped="1">
      <testsuite name="core" tests="2" failures="1" errors="0" skipped="1">
        <testcase classname="example.CoreTest" name="works"/>
        <testcase classname="example.CoreTest" name="fails">
          <failure message="expected true">stack trace</failure>
          <skipped/>
        </testcase>
      </testsuite>
      <testsuite name="api" tests="1" failures="0" errors="1" skipped="0">
        <testcase classname="example.ApiTest" name="loads">
          <error message="boom">error trace</error>
        </testcase>
      </testsuite>
    </testsuites>"""

    report = parse_junit_report(write_xml(tmp_path, payload))

    assert (report.tests, report.failures, report.errors, report.skipped) == (3, 1, 1, 1)
    assert [problem.suite for problem in report.problems] == ["core", "api"]
    assert [problem.kind for problem in report.problems] == ["failure", "error"]
    assert report.problems[0].testcase == "example.CoreTest#fails"


def test_parser_accepts_testsuite_and_absent_optional_fields(tmp_path: Path) -> None:
    """A suite root and testcase with only a name remain valid evidence."""
    payload = '<testsuite tests="1"><testcase name="works"/></testsuite>'

    report = parse_junit_report(write_xml(tmp_path, payload))

    assert (report.tests, report.failures, report.errors, report.skipped) == (1, 0, 0, 0)
    assert report.problems == ()


def test_parser_truncates_problem_messages_and_details(tmp_path: Path) -> None:
    """Failure details are useful but capped before artifact publication."""
    payload = """<testsuite tests="1" failures="1"><testcase name="fails">
      <failure message="{}">{}</failure>
    </testcase></testsuite>""".format("m" * 700, "d" * 700)

    problem = parse_junit_report(write_xml(tmp_path, payload)).problems[0]

    assert len(problem.message) == MAX_REPAIR_TEXT_CHARS
    assert problem.message.endswith("...")
    assert len(problem.details) == MAX_REPAIR_TEXT_CHARS


def test_parser_enforces_problem_limit(tmp_path: Path) -> None:
    """JUnit failures share the bounded finding-count resource limit."""
    payload = """<testsuite tests="1" failures="1"><testcase name="fails">
      <failure>bad</failure>
    </testcase></testsuite>"""

    with pytest.raises(JavaXmlError, match="finding limit"):
        parse_junit_report(write_xml(tmp_path, payload), limits=XmlLimits(max_findings=0))


@pytest.mark.parametrize(
    ("payload", "message"),
    (
        ("<testsuite>", "malformed"),
        ("<not-junit/>", "root"),
        (
            '<testsuite tests="2"><testcase name="only"/></testsuite>',
            "declared tests",
        ),
        (
            '<testsuite tests="1" failures="1"><testcase name="only"/></testsuite>',
            "declared failures",
        ),
        (
            '<testsuite tests="many"><testcase name="only"/></testsuite>',
            "malformed count",
        ),
        (
            '<!DOCTYPE testsuite SYSTEM "file:///etc/passwd"><testsuite/>',
            "DTD or entity",
        ),
    ),
)
def test_parser_rejects_unsafe_or_incomplete_reports(
    tmp_path: Path,
    payload: str,
    message: str,
) -> None:
    """Unsafe, malformed, and count-incomplete JUnit evidence fails closed."""
    with pytest.raises(JavaXmlError, match=message):
        parse_junit_report(write_xml(tmp_path, payload))


def write_xml(root: Path, payload: str) -> Path:
    """Write one JUnit report fixture."""
    report = root / "junit.xml"
    report.write_text(payload, encoding=TEXT_ENCODING)
    return report
