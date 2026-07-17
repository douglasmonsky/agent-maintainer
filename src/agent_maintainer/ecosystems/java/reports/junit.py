"""Bounded JUnit XML report adapter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_maintainer.ecosystems.java.reports.xml import (
    JavaXmlError,
    XmlElement,
    XmlLimits,
    bounded_report_text,
    local_name,
    parse_bounded_xml,
)

COUNT_FIELDS = ("tests", "failures", "errors", "skipped")


@dataclass(frozen=True)
class JUnitProblem:
    """One bounded JUnit failure or error."""

    suite: str
    testcase: str
    kind: str
    message: str
    details: str


@dataclass(frozen=True)
class JUnitReport:
    """Validated JUnit totals and actionable problems."""

    tests: int
    failures: int
    errors: int
    skipped: int
    problems: tuple[JUnitProblem, ...]


@dataclass(frozen=True)
class _Summary:
    tests: int
    failures: int
    errors: int
    skipped: int
    problems: tuple[JUnitProblem, ...]

    def __add__(self, other: _Summary) -> _Summary:
        return _Summary(
            self.tests + other.tests,
            self.failures + other.failures,
            self.errors + other.errors,
            self.skipped + other.skipped,
            (*self.problems, *other.problems),
        )


EMPTY_SUMMARY = _Summary(0, 0, 0, 0, ())


def parse_junit_report(
    path: Path,
    *,
    limits: XmlLimits | None = None,
) -> JUnitReport:
    """Parse suite totals and failure details from bounded JUnit XML."""
    selected_limits = limits or XmlLimits()
    root = parse_bounded_xml(path, limits=selected_limits)
    root_name = local_name(root.tag)
    if root_name == "testsuite":
        summary = _parse_suite(root)
    elif root_name == "testsuites":
        summary = _parse_suites(root)
    else:
        raise JavaXmlError("unsupported JUnit report root")
    if len(summary.problems) > selected_limits.max_findings:
        raise JavaXmlError("JUnit report exceeds finding limit")
    return JUnitReport(
        summary.tests,
        summary.failures,
        summary.errors,
        summary.skipped,
        summary.problems,
    )


def _parse_suites(element: XmlElement) -> _Summary:
    summary = EMPTY_SUMMARY
    for child in element:
        if local_name(child.tag) == "testsuite":
            summary += _parse_suite(child)
    _validate_declared_counts(element, summary)
    return summary


def _parse_suite(element: XmlElement) -> _Summary:
    suite_name = bounded_report_text(element.attrib.get("name", ""))
    direct_cases = tuple(child for child in element if local_name(child.tag) == "testcase")
    summary = _parse_cases(direct_cases, suite_name=suite_name)
    for child in element:
        if local_name(child.tag) == "testsuite":
            summary += _parse_suite(child)
    _validate_declared_counts(element, summary)
    return summary


def _parse_cases(cases: tuple[XmlElement, ...], *, suite_name: str) -> _Summary:
    failures = 0
    errors = 0
    skipped = 0
    problems: list[JUnitProblem] = []
    for case in cases:
        case_problems = _parse_case_problems(case, suite_name=suite_name)
        failures += sum(problem.kind == "failure" for problem in case_problems)
        errors += sum(problem.kind == "error" for problem in case_problems)
        skipped += sum(local_name(child.tag) == "skipped" for child in case)
        problems.extend(case_problems)
    return _Summary(len(cases), failures, errors, skipped, tuple(problems))


def _parse_case_problems(
    element: XmlElement,
    *,
    suite_name: str,
) -> tuple[JUnitProblem, ...]:
    name = element.attrib.get("name", "").strip()
    if not name:
        raise JavaXmlError("JUnit testcase name is missing")
    class_name = element.attrib.get("classname", "").strip()
    testcase = f"{class_name}#{name}" if class_name else name
    return tuple(
        _parse_problem(child, suite_name=suite_name, testcase=testcase)
        for child in element
        if local_name(child.tag) in {"failure", "error"}
    )


def _parse_problem(
    element: XmlElement,
    *,
    suite_name: str,
    testcase: str,
) -> JUnitProblem:
    kind = local_name(element.tag)
    return JUnitProblem(
        suite=suite_name,
        testcase=testcase,
        kind=kind,
        message=bounded_report_text(element.attrib.get("message", ""), fallback=kind),
        details=bounded_report_text("".join(element.itertext())),
    )


def _validate_declared_counts(element: XmlElement, summary: _Summary) -> None:
    actual = dict(
        zip(
            COUNT_FIELDS,
            (summary.tests, summary.failures, summary.errors, summary.skipped),
            strict=True,
        ),
    )
    for field in COUNT_FIELDS:
        value = element.attrib.get(field)
        if value is None:
            continue
        try:
            declared = int(value)
        except ValueError as exc:
            raise JavaXmlError(f"malformed count in JUnit report: {field}") from exc
        if declared < 0:
            raise JavaXmlError(f"malformed count in JUnit report: {field}")
        if declared != actual[field]:
            raise JavaXmlError(f"JUnit declared {field} count is incomplete")
