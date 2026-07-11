"""Parse pytest and coverage exact repair facts."""

from __future__ import annotations

import importlib
from collections.abc import Iterator
from typing import Protocol, TypeGuard

from agent_repair_facts import payloads


class XmlElement(Protocol):
    """Element interface returned by the optional safe XML parser."""

    tag: str
    text: str | None

    def get(self, key: str, default: str | None = None) -> str | None:
        """Return one XML attribute."""

        raise NotImplementedError

    def __len__(self) -> int:
        """Return the number of child elements."""

        raise NotImplementedError

    def __getitem__(self, index: int) -> XmlElement:
        """Return one child element."""

        raise NotImplementedError

    def iter(self, tag: str) -> Iterator[XmlElement]:
        """Iterate over descendants matching a tag."""

        raise NotImplementedError


def is_xml_element(value: object) -> TypeGuard[XmlElement]:
    """Return whether a safe-parser value exposes the required XML API."""

    tag = getattr(value, "tag", None)
    text = getattr(value, "text", None)
    return all(
        (
            isinstance(tag, str),
            text is None or isinstance(text, str),
            callable(getattr(value, "get", None)),
            callable(getattr(value, "__len__", None)),
            callable(getattr(value, "__getitem__", None)),
            callable(getattr(value, "iter", None)),
        ),
    )


def pytest_artifact_facts(
    path: payloads.FactSource,
    check: str,
) -> list[dict[str, object]]:
    """Return pytest facts from JUnit XML or coverage JSON artifacts."""

    if path.name.endswith("pytest-junit.xml"):
        return junit_facts(path, check)
    if path.name == "coverage.json":
        return coverage_facts(path, check)
    return []


def junit_facts(path: payloads.FactSource, check: str) -> list[dict[str, object]]:
    """Return exact facts from pytest JUnit XML output."""

    root = parse_junit_root(path)
    if root is None:
        return []
    return [
        junit_fact(check, case, outcome)
        for case in root.iter("testcase")
        for outcome in first_failure_or_error(case)
    ]


def parse_junit_root(path: payloads.FactSource) -> XmlElement | None:
    """Return safely parsed JUnit XML root when defusedxml is available."""

    try:
        safe_element_tree = importlib.import_module("defusedxml.ElementTree")
    except ImportError:
        return None
    parse_error = getattr(safe_element_tree, "ParseError", ValueError)
    try:
        root = safe_element_tree.fromstring(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, parse_error):
        return None
    return root if is_xml_element(root) else None


def junit_fact(
    check: str,
    case: XmlElement,
    outcome: XmlElement,
) -> dict[str, object]:
    """Return one pytest JUnit exact fact."""

    fallback = payloads.python_location_from_text(outcome.text)
    return payloads.fact_payload(
        {
            "check": check,
            "path": case.get("file") or fallback.get("path"),
            "line": payloads.optional_int(case.get("line")) or fallback.get("line"),
            "column": None,
            "symbol": f"pytest-{local_name(outcome)}",
            "message": junit_message(case, outcome),
            "severity": "error",
        },
    )


def coverage_facts(path: payloads.FactSource, check: str) -> list[dict[str, object]]:
    """Return exact facts from coverage.py JSON output."""

    payload = payloads.json_object(payloads.read_json(path))
    if payload is None:
        return []
    files = payloads.json_object(payload.get("files"))
    if files is None:
        return []
    facts: list[dict[str, object]] = []
    for file_path, raw_file_payload in files.items():
        file_payload = payloads.json_object(raw_file_payload)
        if file_payload is not None and coverage_file_has_missing_lines(file_payload):
            facts.append(coverage_fact(check, file_path, file_payload))
    return facts


def coverage_fact(
    check: str,
    file_path: str,
    file_payload: dict[str, object],
) -> dict[str, object]:
    """Return one coverage exact fact."""

    missing_lines = payloads.json_array(file_payload.get("missing_lines")) or []
    missing_count = len(missing_lines)
    return payloads.fact_payload(
        {
            "check": check,
            "path": file_path,
            "line": payloads.first_int(missing_lines),
            "column": None,
            "symbol": "coverage",
            "message": f"{missing_count} uncovered line(s) in file.",
            "severity": "error",
        },
    )


def first_failure_or_error(case: XmlElement) -> list[XmlElement]:
    """Return first pytest JUnit failure/error child when present."""

    return [
        child
        for index in range(len(case))
        if local_name(child := case[index]) in {"failure", "error"}
    ][:1]


def junit_message(case: XmlElement, outcome: XmlElement) -> str:
    """Return compact pytest JUnit failure message."""

    detail = payloads.optional_text(outcome.get("message")) or payloads.optional_text(
        outcome.text,
    )
    test_id = "::".join(
        part_text
        for part in (case.get("classname"), case.get("name"))
        if (part_text := payloads.optional_text(part))
    )
    return f"{test_id}: {detail}" if detail and test_id else detail or test_id


def coverage_file_has_missing_lines(file_payload: dict[str, object]) -> bool:
    """Return whether coverage JSON file payload has uncovered lines."""

    missing_lines = payloads.json_array(file_payload.get("missing_lines"))
    return bool(missing_lines)


def local_name(element: XmlElement) -> str:
    """Return XML tag local name without namespace."""

    return element.tag.rsplit("}", maxsplit=1)[-1]
