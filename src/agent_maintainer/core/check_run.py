"""Check execution metadata helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class CheckRun:
    """Metadata captured for one check execution."""

    log_path: Path
    started_at: str
    ended_at: str


def utc_timestamp() -> str:
    """Return a stable UTC timestamp for verifier metadata."""

    return datetime.now(tz=UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
