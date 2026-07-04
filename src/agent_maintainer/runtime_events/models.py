"""Runtime event data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Final

from agent_maintainer.runtime_events.redaction import sanitize_attributes

SCHEMA_VERSION: Final = 1
VALID_SEVERITIES: Final = frozenset(("debug", "info", "warning", "error"))


def _empty_attributes() -> dict[str, Any]:
    return {}


@dataclass(frozen=True)
class RuntimeEvent:
    """One compact local runtime event."""

    event_name: str
    severity: str = "info"
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    command: str | None = None
    profile: str | None = None
    run_id: str | None = None
    check: str | None = None
    hook_id: str | None = None
    status: str | None = None
    duration_ms: int | None = None
    exit_code: int | None = None
    repo_configured: bool | None = None
    sensitive: bool = False
    attributes: dict[str, Any] = field(default_factory=_empty_attributes)

    def to_record(self) -> dict[str, Any]:
        """Return JSON-serializable event record."""
        if not self.event_name.strip():
            raise ValueError("event_name must not be empty")
        if self.severity not in VALID_SEVERITIES:
            raise ValueError(f"invalid runtime event severity: {self.severity}")
        record: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "event_name": self.event_name,
            "timestamp": _timestamp_text(self.timestamp),
            "severity": self.severity,
            "sensitive": self.sensitive,
        }
        optional_values = {
            "command": self.command,
            "profile": self.profile,
            "run_id": self.run_id,
            "check": self.check,
            "hook_id": self.hook_id,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "exit_code": self.exit_code,
            "repo_configured": self.repo_configured,
        }
        record.update(
            {key: value for key, value in optional_values.items() if value is not None},
        )
        record["attributes"] = sanitize_attributes(self.attributes)
        return record


def _timestamp_text(timestamp: datetime) -> str:
    aware = timestamp.replace(tzinfo=UTC) if timestamp.tzinfo is None else timestamp
    return aware.astimezone(UTC).isoformat().replace("+00:00", "Z")
