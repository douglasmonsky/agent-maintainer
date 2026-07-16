"""Secure bounded XML input for Java report adapters."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from defusedxml import ElementTree as DefusedET
from defusedxml.common import DefusedXmlException

from agent_maintainer.ecosystems.java.errors import JavaConfigurationError

DEFAULT_MAX_XML_BYTES = 5_242_880
DEFAULT_MAX_XML_ELEMENTS = 50_000
DEFAULT_MAX_FINDINGS = 10_000
DEFAULT_MAX_MESSAGE_CHARS = 2_000
MAX_REPAIR_TEXT_CHARS = 500
XML_INDENT = "  "
WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")
type XmlElement = Any


class JavaXmlError(JavaConfigurationError):
    """Raised when Java report XML is unsafe, malformed, or over limits."""


@dataclass(frozen=True)
class XmlLimits:
    """Explicit parser resource limits."""

    max_bytes: int = DEFAULT_MAX_XML_BYTES
    max_elements: int = DEFAULT_MAX_XML_ELEMENTS
    max_findings: int = DEFAULT_MAX_FINDINGS
    max_message_chars: int = DEFAULT_MAX_MESSAGE_CHARS


def parse_bounded_xml(path: Path, *, limits: XmlLimits) -> XmlElement:
    """Read and parse XML after declaration and byte-size checks."""
    payload = _read_xml_bytes(path, limits)
    _reject_declarations(payload)
    try:
        root = DefusedET.fromstring(payload)
    except (DefusedET.ParseError, DefusedXmlException) as exc:
        raise JavaXmlError("malformed Java XML report") from exc
    _validate_tree_limits(root, limits)
    return root


def local_name(tag: str) -> str:
    """Return one namespace-independent XML tag name."""
    return tag.rsplit("}", maxsplit=1)[-1]


def bounded_report_text(value: str, *, fallback: str = "") -> str:
    """Normalize report text and cap details published as repair facts."""
    normalized = " ".join(value.split()) or fallback
    if len(normalized) <= MAX_REPAIR_TEXT_CHARS:
        return normalized
    prefix = normalized[: MAX_REPAIR_TEXT_CHARS - 3]
    return f"{prefix}..."


def normalized_report_path(value: str, *, gradle_root: Path) -> str:
    """Return a report source path confined beneath the Gradle root."""
    normalized = value.strip().replace("\\", "/")
    source_path = PurePosixPath(normalized)
    if not normalized or WINDOWS_DRIVE.match(normalized) or ".." in source_path.parts:
        raise JavaXmlError("Java report source path is not repository-relative")
    root = gradle_root.resolve()
    candidate = Path(normalized)
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        relative = candidate.resolve().relative_to(root)
    except (OSError, ValueError) as exc:
        raise JavaXmlError("Java report source path escapes Gradle root") from exc
    if relative == Path("."):
        raise JavaXmlError("Java report source path is not a file")
    return relative.as_posix()


def new_xml_element(tag: str) -> XmlElement:
    """Create one trusted internal XML element."""
    return DefusedET.fromstring(f"<{tag}/>")


def append_xml_element(
    parent: XmlElement,
    tag: str,
    attributes: dict[str, str],
) -> XmlElement:
    """Append one trusted internal XML child."""
    child = parent.makeelement(tag, attributes)
    parent.append(child)
    return child


def serialize_xml(root: XmlElement) -> str:
    """Serialize one trusted tree with deterministic indentation."""
    _indent_xml(root)
    return DefusedET.tostring(root, encoding="unicode", short_empty_elements=True)


def _read_xml_bytes(path: Path, limits: XmlLimits) -> bytes:
    try:
        report_size = path.stat().st_size
    except OSError as exc:
        raise JavaXmlError(f"cannot read Java XML report: {path.name}") from exc
    if report_size > limits.max_bytes:
        raise JavaXmlError("Java XML report exceeds byte limit")
    return _read_limited_bytes(path, limits.max_bytes)


def _read_limited_bytes(path: Path, max_bytes: int) -> bytes:
    try:
        with path.open("rb") as report:
            payload = report.read(max_bytes + 1)
    except OSError as exc:
        raise JavaXmlError(f"cannot read Java XML report: {path.name}") from exc
    if len(payload) > max_bytes:
        raise JavaXmlError("Java XML report exceeds byte limit")
    return payload


def _reject_declarations(payload: bytes) -> None:
    lowered = payload.lower()
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        raise JavaXmlError("Java XML report contains a forbidden DTD or entity declaration")


def _validate_tree_limits(root: XmlElement, limits: XmlLimits) -> None:
    for element_count, element in enumerate(root.iter(), start=1):
        if element_count > limits.max_elements:
            raise JavaXmlError("Java XML report exceeds element limit")
        values = (*element.attrib.values(), element.text or "", element.tail or "")
        if any(len(value.strip()) > limits.max_message_chars for value in values):
            raise JavaXmlError("Java XML report exceeds message limit")


def _indent_xml(element: XmlElement, level: int = 0) -> None:
    indentation = "".join(("\n", XML_INDENT * level))
    children = tuple(element)
    if not children:
        return
    if not element.text or not element.text.strip():
        element.text = "".join((indentation, XML_INDENT))
    for child in children:
        _indent_xml(child, level + 1)
    last_child = children[-1]
    if not last_child.tail or not last_child.tail.strip():
        last_child.tail = indentation
