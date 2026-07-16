"""Exact repair facts from sanitized Java Gradle run artifacts."""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from agent_repair_facts.payloads import (
    FactSource,
    fact_payload,
    json_object,
    json_objects,
    optional_int,
    optional_text,
    read_json,
)

MAX_JAVA_FACTS = 10
MAX_JAVA_FACT_TEXT = 500
MAX_JAVA_PATH_TEXT = 1_000
WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")


def java_artifact_facts(source: FactSource, check: str) -> list[dict[str, object]]:
    """Return capped exact facts from one already-read Java artifact."""
    payload = json_object(read_json(source))
    if payload is None or payload.get("provider") != "java-gradle":
        return []
    if optional_int(payload.get("schema_version")) != 1:
        return []
    reports = json_object(payload.get("reports"))
    if reports is None:
        return []
    facts = _test_problem_facts(reports, check)
    facts.extend(_finding_facts(reports, check))
    return facts[:MAX_JAVA_FACTS]


def _finding_facts(reports: dict[str, object], check: str) -> list[dict[str, object]]:
    return [
        fact
        for finding in json_objects(reports.get("findings"))
        if (fact := _finding_fact(finding, check)) is not None
    ]


def _finding_fact(
    finding: dict[str, object],
    check: str,
) -> dict[str, object] | None:
    rule = optional_text(finding.get("rule"))
    message = optional_text(finding.get("message"))
    if rule is None or message is None:
        return None
    return fact_payload(
        {
            "check": check,
            "path": _safe_path(finding.get("path")),
            "line": _positive_int(finding.get("line")),
            "column": None,
            "symbol": _bounded_text(rule),
            "message": _bounded_text(message),
            "severity": finding.get("severity"),
        },
    )


def _test_problem_facts(reports: dict[str, object], check: str) -> list[dict[str, object]]:
    tests = json_object(reports.get("tests"))
    if tests is None:
        return []
    return [
        fact
        for problem in json_objects(tests.get("problems"))
        if (fact := _test_problem_fact(problem, check)) is not None
    ]


def _test_problem_fact(
    problem: dict[str, object],
    check: str,
) -> dict[str, object] | None:
    testcase = optional_text(problem.get("testcase"))
    message = optional_text(problem.get("message"))
    if testcase is None or message is None:
        return None
    kind = optional_text(problem.get("kind")) or "failure"
    return fact_payload(
        {
            "check": check,
            "path": None,
            "line": None,
            "column": None,
            "symbol": _bounded_text(testcase),
            "message": _bounded_text(f"{kind}: {message}"),
            "severity": "error",
        },
    )


def _safe_path(value: object) -> str | None:
    raw_path = optional_text(value)
    if raw_path is None:
        return None
    normalized = raw_path.replace("\\", "/")
    path = PurePosixPath(normalized)
    unsafe = (
        path.as_posix() == "."
        or path.is_absolute()
        or ".." in path.parts
        or WINDOWS_DRIVE.match(normalized)
    )
    if unsafe:
        return None
    return _bounded_text(path.as_posix(), limit=MAX_JAVA_PATH_TEXT)


def _positive_int(value: object) -> int | None:
    parsed = optional_int(value)
    return parsed if parsed is not None and parsed > 0 else None


def _bounded_text(value: str, *, limit: int = MAX_JAVA_FACT_TEXT) -> str:
    return " ".join(value.split())[:limit]
