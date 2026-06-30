"""Parse pytest and coverage exact repair facts."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from agent_maintainer.context.pack.fact_payloads import (
    fact_payload,
    first_int,
    optional_int,
    optional_text,
    python_location_from_text,
    read_json,
)


def pytest_artifact_facts(path: Path, check: str) -> list[dict[str, object]]:
    """Return pytest facts from JUnit XML or coverage JSON artifacts."""

    if path.name.endswith("pytest-junit.xml"):
        return junit_facts(path, check)
    if path.name == "coverage.json":
        return coverage_facts(path, check)
    return []


def junit_facts(path: Path, check: str) -> list[dict[str, object]]:
    """Return exact facts from pytest JUnit XML output."""

    root = parse_junit_root(path)
    if root is None:
        return []
    return [
        junit_fact(check, case, outcome)
        for case in root.iter("testcase")
        for outcome in first_failure_or_error(case)
    ]


def parse_junit_root(path: Path) -> Any | None:
    """Return safely parsed JUnit XML root when defusedxml is available."""

    try:
        safe_element_tree = importlib.import_module("defusedxml.ElementTree")
    except ImportError:
        return None
    parse_error = getattr(safe_element_tree, "ParseError", ValueError)
    try:
        return safe_element_tree.parse(path).getroot()
    except (OSError, parse_error):
        return None


def junit_fact(
    check: str,
    case: Any,
    outcome: Any,
) -> dict[str, object]:
    """Return one pytest JUnit exact fact."""

    fallback = python_location_from_text(outcome.text)
    return fact_payload(
        {
            "check": check,
            "path": case.get("file") or fallback.get("path"),
            "line": optional_int(case.get("line")) or fallback.get("line"),
            "column": None,
            "symbol": f"pytest-{local_name(outcome)}",
            "message": junit_message(case, outcome),
            "severity": "error",
        },
    )


def coverage_facts(path: Path, check: str) -> list[dict[str, object]]:
    """Return exact facts from coverage.py JSON output."""

    payload = read_json(path)
    if not isinstance(payload, dict):
        return []
    files = payload.get("files", {})
    if not isinstance(files, dict):
        return []
    return [
        coverage_fact(check, file_path, file_payload)
        for file_path, file_payload in files.items()
        if isinstance(file_payload, dict) and coverage_file_has_missing_lines(file_payload)
    ]


def coverage_fact(
    check: str,
    file_path: object,
    file_payload: dict[str, Any],
) -> dict[str, object]:
    """Return one coverage exact fact."""

    missing_lines = file_payload.get("missing_lines", [])
    missing_count = len(missing_lines) if isinstance(missing_lines, list) else 0
    return fact_payload(
        {
            "check": check,
            "path": file_path,
            "line": first_int(missing_lines),
            "column": None,
            "symbol": "coverage",
            "message": f"{missing_count} uncovered line(s) in file.",
            "severity": "error",
        },
    )


def first_failure_or_error(case: Any) -> list[Any]:
    """Return first pytest JUnit failure/error child when present."""

    return [child for child in case if local_name(child) in {"failure", "error"}][:1]


def junit_message(case: Any, outcome: Any) -> str:
    """Return compact pytest JUnit failure message."""

    detail = optional_text(outcome.get("message")) or optional_text(outcome.text)
    test_id = "::".join(
        part_text
        for part in (case.get("classname"), case.get("name"))
        if (part_text := optional_text(part))
    )
    return f"{test_id}: {detail}" if detail and test_id else detail or test_id


def coverage_file_has_missing_lines(file_payload: dict[str, Any]) -> bool:
    """Return whether coverage JSON file payload has uncovered lines."""

    missing_lines = file_payload.get("missing_lines", [])
    return isinstance(missing_lines, list) and bool(missing_lines)


def local_name(element: Any) -> str:
    """Return XML tag local name without namespace."""

    return element.tag.rsplit("}", maxsplit=1)[-1]
