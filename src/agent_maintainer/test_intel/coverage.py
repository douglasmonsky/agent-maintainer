"""Coverage artifact helpers for test intelligence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from defusedxml import ElementTree as DEFUSED_ELEMENT_TREE
except ModuleNotFoundError:
    DEFUSED_ELEMENT_TREE = None

from agent_maintainer.test_intel.models import CoverageSummary


def coverage_for_changed_sources(
    repo_root: Path,
    changed_source: tuple[str, ...],
) -> CoverageSummary:
    """Return coverage summary for changed source when artifacts exist."""

    if not changed_source:
        return CoverageSummary()
    json_summary = coverage_from_json(repo_root / "coverage.json", changed_source)
    if json_summary.changed_line_coverage is not None:
        return json_summary
    return coverage_from_xml(repo_root / "coverage.xml", changed_source)


def coverage_from_json(path: Path, changed_source: tuple[str, ...]) -> CoverageSummary:
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
    return CoverageSummary(changed_line_coverage=average(percentages))


def json_file_percent(entry: object) -> float | None:
    """Return one file coverage percent from coverage.py JSON entry."""

    if not isinstance(entry, dict):
        return None
    summary = entry.get("summary", {})
    if not isinstance(summary, dict):
        return None
    percent = summary.get("percent_covered")
    return float(percent) if isinstance(percent, int | float) else None


def coverage_from_xml(path: Path, changed_source: tuple[str, ...]) -> CoverageSummary:
    """Return coverage summary from Cobertura-style XML output."""

    element_tree = safe_element_tree()
    if element_tree is None:
        return CoverageSummary()
    try:
        root = element_tree.parse(path).getroot()
    except (OSError, element_tree.ParseError):
        return CoverageSummary()
    rates = [rate for source in changed_source if (rate := xml_file_rate(root, source)) is not None]
    percent = average([rate * 100 for rate in rates])
    return CoverageSummary(changed_line_coverage=percent)


def xml_file_rate(root: Any, source: str) -> float | None:
    """Return XML line-rate for one source path."""

    for class_node in root.findall(".//class"):
        filename = str(class_node.attrib.get("filename", "")).replace("\\", "/")
        if filename == source:
            value = class_node.attrib.get("line-rate")
            if value is None:
                return None
            try:
                return float(value)
            except ValueError:
                return None
    return None


def safe_element_tree() -> Any | None:
    """Return defused ElementTree module when installed."""

    return DEFUSED_ELEMENT_TREE


def average(values: list[float]) -> float | None:
    """Return average rounded percentage when values are present."""

    if values:
        return round(sum(values) / len(values), 2)
    return None
