"""Secure bounded XML input for Java report adapters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from defusedxml import ElementTree as DefusedET
from defusedxml.common import DefusedXmlException

from agent_maintainer.ecosystems.java.errors import JavaConfigurationError

DEFAULT_MAX_XML_BYTES = 5_242_880
DEFAULT_MAX_XML_ELEMENTS = 50_000
DEFAULT_MAX_FINDINGS = 10_000
DEFAULT_MAX_MESSAGE_CHARS = 2_000
XML_INDENT = "  "
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
        size, payload = path.stat().st_size, path.read_bytes()
    except OSError as exc:
        raise JavaXmlError(f"cannot read Java XML report: {path.name}") from exc
    if size > limits.max_bytes:
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
