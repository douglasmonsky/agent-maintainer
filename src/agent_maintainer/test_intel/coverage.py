"""Coverage artifact helpers for test intelligence."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

try:
    from defusedxml import ElementTree as DEFUSED_ELEMENT_TREE
except ModuleNotFoundError:
    DEFUSED_ELEMENT_TREE = None

from agent_maintainer.test_intel import coverage_lines
from agent_maintainer.test_intel.models import CoverageSummary


def coverage_for_changed_sources(
    repo_root: Path,
    changed_source: tuple[str, ...],
    *,
    base_ref: str | None = None,
    staged: bool = False,
) -> CoverageSummary:
    """Return coverage summary for changed source when artifacts exist."""
    if not changed_source:
        return CoverageSummary()

    changed_lines = changed_line_numbers_for_ref(
        repo_root,
        changed_source,
        base_ref=base_ref,
        staged=staged,
    )
    json_summary = coverage_from_json(
        repo_root / "coverage.json",
        changed_source,
        changed_lines,
    )
    if (
        json_summary.changed_source_file_coverage is not None
        or json_summary.changed_line_coverage is not None
    ):
        return json_summary
    return coverage_from_xml(repo_root / "coverage.xml", changed_source, changed_lines)


def changed_line_numbers_for_ref(
    repo_root: Path,
    changed_source: tuple[str, ...],
    *,
    base_ref: str | None,
    staged: bool,
) -> Mapping[str, frozenset[int]]:
    """Return changed-line map when diff context is available."""
    if base_ref is None:
        return {}
    return coverage_lines.changed_line_numbers(
        repo_root,
        changed_source,
        base_ref=base_ref,
        staged=staged,
    )


def coverage_from_json(
    path: Path,
    changed_source: tuple[str, ...],
    changed_lines: Mapping[str, frozenset[int]] | None = None,
) -> CoverageSummary:
    """Return coverage summary from coverage.py JSON output."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return CoverageSummary()
    files = payload.get("files", {})
    if not isinstance(files, dict):
        return CoverageSummary()
    percentages = [
        percent
        for source in changed_source
        if (percent := json_file_percent(files.get(source))) is not None
    ]
    return CoverageSummary(
        changed_source_file_coverage=average(percentages),
        changed_line_coverage=json_changed_line_percent(files, changed_lines),
    )


def json_file_percent(entry: object) -> float | None:
    """Return one file coverage percent from coverage.py JSON entry."""
    if not isinstance(entry, dict):
        return None
    summary = entry.get("summary", {})
    if not isinstance(summary, dict):
        return None
    percent = summary.get("percent_covered")
    return float(percent) if isinstance(percent, int | float) else None


def json_changed_line_percent(
    files: dict[object, object],
    changed_lines: Mapping[str, frozenset[int]] | None,
) -> float | None:
    """Return changed-line coverage from coverage.py JSON output."""
    percentages: list[float] = []
    for source, lines in coverage_lines.changed_line_map(changed_lines).items():
        covered_lines, missing_lines = json_line_sets(files.get(source))
        percent = coverage_lines.line_coverage_percent(
            lines,
            covered_lines,
            missing_lines,
        )
        if percent is not None:
            percentages.append(percent)
    return average(percentages)


def json_line_sets(entry: object) -> tuple[frozenset[int], frozenset[int]]:
    """Return covered and missing executable lines from JSON entry."""
    if not isinstance(entry, dict):
        return frozenset(), frozenset()
    return (
        coverage_lines.int_line_set(entry.get("executed_lines")),
        coverage_lines.int_line_set(entry.get("missing_lines")),
    )


def coverage_from_xml(
    path: Path,
    changed_source: tuple[str, ...],
    changed_lines: Mapping[str, frozenset[int]] | None = None,
) -> CoverageSummary:
    """Return coverage summary from Cobertura-style XML output."""
    element_tree = safe_element_tree()
    if element_tree is None:
        return CoverageSummary()
    try:
        root = element_tree.parse(path).getroot()
    except (OSError, element_tree.ParseError):
        return CoverageSummary()
    rates = [rate for source in changed_source if (rate := xml_file_rate(root, source)) is not None]
    percent = average([rate * coverage_lines.PERCENT_SCALE for rate in rates])
    return CoverageSummary(
        changed_source_file_coverage=percent,
        changed_line_coverage=xml_changed_line_percent(root, changed_lines),
    )


def xml_file_rate(root: Any, source: str) -> float | None:
    """Return XML line-rate for one source path."""
    for class_node in matching_class_nodes(root, source):
        value = class_node.attrib.get("line-rate")
        if value is None:
            return None
        try:
            return float(value)
        except ValueError:
            return None
    return None


def xml_changed_line_percent(
    root: Any,
    changed_lines: Mapping[str, frozenset[int]] | None,
) -> float | None:
    """Return changed-line coverage from Cobertura-style XML output."""
    percentages: list[float] = []
    for source, lines in coverage_lines.changed_line_map(changed_lines).items():
        covered_lines, missing_lines = xml_line_sets(root, source)
        percent = coverage_lines.line_coverage_percent(
            lines,
            covered_lines,
            missing_lines,
        )
        if percent is not None:
            percentages.append(percent)
    return average(percentages)


def xml_line_sets(root: Any, source: str) -> tuple[frozenset[int], frozenset[int]]:
    """Return covered and missing executable lines from XML classes."""
    covered_lines: set[int] = set()
    missing_lines: set[int] = set()
    for class_node in matching_class_nodes(root, source):
        for line_node in class_node.findall("./lines/line"):
            line_number = int(line_node.attrib.get("number", "0"))
            if int(line_node.attrib.get("hits", "0")) > 0:
                covered_lines.add(line_number)
            else:
                missing_lines.add(line_number)
    return frozenset(covered_lines), frozenset(missing_lines)


def matching_class_nodes(root: Any, source: str) -> list[Any]:
    """Return XML class nodes for one source path."""
    return [
        class_node
        for class_node in root.findall(".//class")
        if str(class_node.attrib.get("filename", "")).replace("\\", "/") == source
    ]


def safe_element_tree() -> Any | None:
    """Return defused ElementTree module when installed."""
    return DEFUSED_ELEMENT_TREE


def average(values: list[float]) -> float | None:
    """Return average rounded percentage when values are present."""
    if values:
        return round(sum(values) / len(values), 2)
    return None
