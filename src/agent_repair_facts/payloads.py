"""Shared exact repair fact payload helpers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

PYTHON_PATH_RE = re.compile(r"(?P<path>[\w./-]+\.py):(?P<line>\d+)")
SUPPORTED_ENCODINGS = frozenset((None, "utf-8"))
SUPPORTED_ERROR_HANDLERS = frozenset((None, "strict", "replace"))


class FactSource(Protocol):
    """Text source accepted by exact repair-fact parsers."""

    @property
    def name(self) -> str:
        """Return the source filename."""

        raise NotImplementedError

    @property
    def suffix(self) -> str:
        """Return the source filename suffix."""

        raise NotImplementedError

    def read_text(
        self,
        encoding: str | None = None,
        errors: str | None = None,
    ) -> str:
        """Return source text."""

        raise NotImplementedError


@dataclass(frozen=True)
class MemoryFactSource:
    """Already-read text exposed through the legacy parser source interface."""

    path: Path
    content: str

    @property
    def name(self) -> str:
        """Return the original source filename."""

        return self.path.name

    @property
    def suffix(self) -> str:
        """Return the original source suffix."""

        return self.path.suffix

    def read_text(
        self,
        encoding: str | None = None,
        errors: str | None = None,
    ) -> str:
        """Return captured text without reopening the original path."""

        if encoding not in SUPPORTED_ENCODINGS:
            raise ValueError(f"unsupported in-memory text encoding: {encoding}")
        if errors not in SUPPORTED_ERROR_HANDLERS:
            raise ValueError(f"unsupported in-memory error handler: {errors}")
        return self.content


def read_json(path: FactSource) -> object | None:
    """Return JSON artifact payload when available."""

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, RecursionError):
        return None


def fact_payload(values: dict[str, object]) -> dict[str, object]:
    """Return normalized exact repair fact payload."""

    return {
        "check": str(values.get("check") or "unknown"),
        "path": optional_text(values.get("path")),
        "line": optional_int(values.get("line")),
        "column": optional_int(values.get("column")),
        "symbol": optional_text(values.get("symbol")),
        "message": str(values.get("message") or "").strip(),
        "severity": lower_text(values.get("severity")) or "error",
    }


def optional_int(value: object) -> int | None:
    """Return integer values from numeric artifact fields."""

    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return None


def optional_text(value: object) -> str | None:
    """Return non-empty string values."""

    if value is None:
        return None
    text = str(value).strip()
    return text or None


def lower_text(value: object) -> str | None:
    """Return lower-cased optional text."""

    text = optional_text(value)
    return text.lower() if text else None


def one_based(value: object) -> int | None:
    """Return one-based integer from zero-based artifact value."""

    integer = optional_int(value)
    return None if integer is None else integer + 1


def first_int(value: object) -> int | None:
    """Return first integer from a list-like value."""

    if not isinstance(value, list):
        return None
    return next((item for item in value if isinstance(item, int)), None)


def location_value(location: object, key: str) -> int | None:
    """Return integer location value from mapping."""

    if not isinstance(location, dict):
        return None
    return optional_int(location.get(key))


def python_location_from_text(text: object) -> dict[str, object]:
    """Return first Python file location embedded in text."""

    content = optional_text(text)
    if not content:
        return {}
    match = PYTHON_PATH_RE.search(content)
    if not match:
        return {}
    return {"path": match.group("path"), "line": optional_int(match.group("line"))}
