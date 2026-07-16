"""Canonical Java finding identity independent of source line movement."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import PurePosixPath

WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")


@dataclass(frozen=True)
class JavaFindingIdentity:
    """Stable semantic fields used to fingerprint one finding."""

    tool: str
    rule: str
    path: str
    subject: str
    message: str
    severity: str


@dataclass(frozen=True)
class JavaFinding:
    """One normalized report finding with an optional numeric measurement."""

    tool: str
    rule: str
    path: str
    subject: str
    message: str
    severity: str = "warning"
    line: int | None = None
    metric: int | None = None

    def __post_init__(self) -> None:
        """Normalize stable identity fields and validate display-only values."""
        object.__setattr__(self, "tool", _required_text(self.tool, "tool").lower())
        object.__setattr__(self, "rule", _required_text(self.rule, "rule"))
        object.__setattr__(self, "path", _normalized_path(self.path))
        object.__setattr__(self, "subject", _normalized_text(self.subject))
        object.__setattr__(self, "message", _required_text(self.message, "message"))
        object.__setattr__(self, "severity", _required_text(self.severity, "severity").lower())
        if self.line is not None and self.line < 1:
            raise ValueError("finding line must be positive")
        if self.metric is not None and self.metric < 0:
            raise ValueError("finding metric must be non-negative")

    @property
    def fingerprint(self) -> str:
        """Return a stable SHA-256 identity excluding line and measurement."""
        payload = json.dumps(
            asdict(self.identity),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @property
    def identity(self) -> JavaFindingIdentity:
        """Return the normalized semantic fields used for debt identity."""
        return JavaFindingIdentity(
            self.tool,
            self.rule,
            self.path,
            self.subject,
            self.message,
            self.severity,
        )


def _normalized_text(value: str) -> str:
    return " ".join(value.split())


def _required_text(value: str, field: str) -> str:
    normalized = _normalized_text(value)
    if not normalized:
        raise ValueError(f"finding {field} must not be empty")
    return normalized


def _normalized_path(value: str) -> str:
    normalized = value.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    path = PurePosixPath(normalized)
    if (
        not normalized
        or path.is_absolute()
        or ".." in path.parts
        or WINDOWS_DRIVE.match(normalized) is not None
    ):
        raise ValueError("finding path must be repository-relative")
    result = path.as_posix()
    if result in {"", "."}:
        raise ValueError("finding path must be repository-relative")
    return result
