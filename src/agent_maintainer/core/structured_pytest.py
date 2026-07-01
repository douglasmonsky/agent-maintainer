"""Structured pytest and coverage artifact summaries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DefusedElementTree: Any
try:
    from defusedxml import ElementTree as DefusedElementTree
except ImportError:
    DefusedElementTree = None

STRUCTURED_DIAGNOSTIC_LIMIT = 50
MISSING_LINE_PREVIEW = 8
COVERAGE_FILE_PREVIEW = 5
CoverageEntry = tuple[int, str, dict[str, object]]


def summarize_pytest_artifacts(artifact_paths: tuple[str, ...]) -> str | None:
    """Summarize pytest JUnit and coverage JSON artifacts together."""

    junit_summary = summarize_junit_artifact(artifact_paths)
    coverage_summary = summarize_coverage_artifact(artifact_paths)
    summaries = [item for item in (junit_summary, coverage_summary) if item]
    return "\n".join(summaries) if summaries else None


def summarize_coverage_artifact(artifact_paths: tuple[str, ...]) -> str | None:
    """Load coverage JSON artifact and summarize totals."""

    path = next((Path(item) for item in artifact_paths if item.endswith("coverage.json")), None)
    if path is None or not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return summarize_coverage_payload(payload)


def summarize_junit_artifact(artifact_paths: tuple[str, ...]) -> str | None:
    """Summarize pytest JUnit XML failures and suite counts."""

    path = next(
        (Path(item) for item in artifact_paths if item.endswith("pytest-junit.xml")),
        None,
    )
    if path is None or not path.exists():
        return None
    if DefusedElementTree is None:
        return None

    try:
        root = DefusedElementTree.parse(path).getroot()
    except (OSError, DefusedElementTree.ParseError):
        return None
    if root is None:
        return None
    suite_stats = junit_suite_stats(root)
    lines = [
        "pytest: "
        f"{suite_stats['tests']} tests, "
        f"{suite_stats['failures']} failures, "
        f"{suite_stats['errors']} errors, "
        f"{suite_stats['skipped']} skipped",
    ]
    lines.extend(junit_issue_lines(root))
    return "\n".join(lines)


def junit_suite_stats(root: Any) -> dict[str, int]:
    """Return aggregate JUnit suite counters."""

    suites = root.findall(".//testsuite") if root.tag == "testsuites" else [root]
    stats = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for suite in suites:
        for key in stats:
            stats[key] += int_attribute(suite, key)
    return stats


def junit_issue_lines(root: Any) -> list[str]:
    """Return compact JUnit testcase failure/error lines."""

    lines: list[str] = []
    for testcase in root.findall(".//testcase"):
        issue = first_testcase_issue(testcase)
        if issue is None:
            continue
        test_name = "::".join(
            item for item in (testcase.get("classname"), testcase.get("name")) if item
        )
        message = first_nonblank(issue.get("message") or issue.text or "")
        lines.append(f"{test_name}: {issue.tag}: {message}")
        if len(lines) >= STRUCTURED_DIAGNOSTIC_LIMIT:
            break
    append_junit_omitted(lines, root)
    return lines


def first_testcase_issue(testcase: Any) -> Any | None:
    """Return first failure or error child for one testcase."""

    return next(
        (child for child in testcase if child.tag in {"failure", "error"}),
        None,
    )


def append_junit_omitted(lines: list[str], root: Any) -> None:
    """Append omitted JUnit failure count when output is capped."""

    omitted = max(0, junit_issue_count(root) - len(lines))
    if omitted:
        lines.append(
            f"... {omitted} more pytest failures omitted. See .verify-logs/pytest-junit.xml"
        )


def junit_issue_count(root: Any) -> int:
    """Return total number of JUnit failure/error elements."""

    return sum(
        1
        for testcase in root.findall(".//testcase")
        for child in testcase
        if child.tag in {"failure", "error"}
    )


def summarize_coverage_payload(payload: object) -> str | None:
    """Summarize coverage JSON totals and worst missing-line files."""

    if not isinstance(payload, dict):
        return None
    totals = payload.get("totals", {})
    files = payload.get("files", {})
    if not isinstance(totals, dict) or not isinstance(files, dict):
        return None
    covered = int_value(totals.get("covered_lines"))
    statements = int_value(totals.get("num_statements"))
    missing = int_value(totals.get("missing_lines"))
    percent = percent_value(totals)
    lines = [f"coverage total: {percent} ({covered}/{statements} lines, {missing} missing)"]
    lines.extend(worst_coverage_file_lines(files))
    return "\n".join(lines)


def worst_coverage_file_lines(files: dict[str, object]) -> list[str]:
    """Return compact coverage lines for files with the most missing lines."""

    entries = coverage_entries(files)
    lines: list[str] = []
    for missing_count, file_name, payload in entries[:COVERAGE_FILE_PREVIEW]:
        summary = payload.get("summary", {})
        percent = percent_value(summary if isinstance(summary, dict) else {})
        missing_lines = payload.get("missing_lines", [])
        preview = line_preview(missing_lines if isinstance(missing_lines, list) else [])
        lines.append(f"{file_name}: {percent}, {missing_count} missing ({preview})")
    if len(entries) > COVERAGE_FILE_PREVIEW:
        hidden = len(entries) - COVERAGE_FILE_PREVIEW
        lines.append(f"... {hidden} more files with missing coverage omitted.")
    return lines


def coverage_entries(files: dict[str, object]) -> list[CoverageEntry]:
    """Return coverage entries sorted by missing-line count."""

    entries: list[CoverageEntry] = []
    for file_name, payload in files.items():
        if not isinstance(payload, dict):
            continue
        missing_lines = payload.get("missing_lines", [])
        if isinstance(missing_lines, list) and missing_lines:
            entries.append((len(missing_lines), file_name, payload))
    return sorted(entries, reverse=True)


def int_attribute(element: Any, name: str) -> int:
    """Return nonnegative integer XML attribute."""

    return int_value(element.get(name))


def int_value(value: object, *, default: int = 0) -> int:
    """Return integer value with safe fallback."""

    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return default
    try:
        return int(value)
    except ValueError:
        return default


def percent_value(summary: dict[str, object]) -> str:
    """Return display coverage percentage from coverage.py summary."""

    display = summary.get("percent_covered_display") or summary.get(
        "percent_statements_covered_display"
    )
    if display is not None:
        return f"{display}%"
    raw_value = summary.get("percent_covered") or summary.get("percent_statements_covered")
    if isinstance(raw_value, int | float):
        return f"{raw_value:.2f}%"
    return "?%"


def line_preview(lines: list[object]) -> str:
    """Return compact preview of missing line numbers."""

    values = [int(item) for item in lines if isinstance(item, int)]
    preview = values[:MISSING_LINE_PREVIEW]
    suffix = ", ..." if len(values) > MISSING_LINE_PREVIEW else ""
    return ", ".join(str(item) for item in preview) + suffix


def first_nonblank(text: str) -> str:
    """Return first nonblank line from text."""

    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""
