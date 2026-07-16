"""Exact bounded JaCoCo bundle coverage parsing."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from agent_maintainer.ecosystems.java.reports import xml as java_xml

PERCENT_QUANTUM = Decimal("0.0001")
PERCENT_MULTIPLIER = Decimal(100)
REQUIRED_COUNTERS = ("LINE", "BRANCH")
JACOCO_REPORT_DOCTYPE = b'<!DOCTYPE report PUBLIC "-//JACOCO//DTD Report 1.1//EN" "report.dtd">'


@dataclass(frozen=True)
class JacocoCounter:
    """One exact JaCoCo counter and its four-place percentage."""

    missed: int
    covered: int

    def __post_init__(self) -> None:
        if self.missed < 0 or self.covered < 0:
            raise java_xml.JavaXmlError("JaCoCo counters must be non-negative integers")

    @property
    def percentage(self) -> Decimal:
        """Return covered / total as a percentage rounded to four places."""
        total = self.missed + self.covered
        if total == 0:
            return Decimal(0).quantize(PERCENT_QUANTUM)
        percentage = Decimal(self.covered) * PERCENT_MULTIPLIER / Decimal(total)
        return percentage.quantize(PERCENT_QUANTUM, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class JacocoCoverage:
    """Report-level line and branch coverage for one truthful scope."""

    line: JacocoCounter
    branch: JacocoCounter


def parse_jacoco_report(path: Path) -> JacocoCoverage:
    """Parse required report-level LINE and BRANCH counters exactly once."""
    root = java_xml.parse_bounded_xml(
        path,
        limits=java_xml.XmlLimits(),
        allowed_doctype=JACOCO_REPORT_DOCTYPE,
    )
    if java_xml.local_name(root.tag) != "report":
        raise java_xml.JavaXmlError("unsupported JaCoCo report root")
    counters = _report_counters(root)
    return JacocoCoverage(line=counters["LINE"], branch=counters["BRANCH"])


def _report_counters(root: java_xml.XmlElement) -> dict[str, JacocoCounter]:
    counters: dict[str, JacocoCounter] = {}
    for element in root:
        if java_xml.local_name(element.tag) != "counter":
            continue
        counter_type = element.attrib.get("type", "")
        if counter_type not in REQUIRED_COUNTERS:
            continue
        if counter_type in counters:
            raise java_xml.JavaXmlError(f"duplicate JaCoCo {counter_type} counter")
        counters[counter_type] = JacocoCounter(
            missed=_counter_value(element, "missed"),
            covered=_counter_value(element, "covered"),
        )
    missing = tuple(counter for counter in REQUIRED_COUNTERS if counter not in counters)
    if missing:
        raise java_xml.JavaXmlError(f"missing JaCoCo report counter: {missing[0]}")
    return counters


def _counter_value(element: java_xml.XmlElement, attribute: str) -> int:
    raw = element.attrib.get(attribute, "")
    if not raw.isdecimal():
        raise java_xml.JavaXmlError(f"invalid JaCoCo {attribute} counter")
    return int(raw)
