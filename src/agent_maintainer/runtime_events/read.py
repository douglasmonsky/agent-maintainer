"""Read local runtime event JSONL artifacts safely."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _empty_records() -> list[dict[str, Any]]:
    return []


@dataclass(frozen=True)
class RuntimeEventReadResult:
    """Runtime event read result with malformed-line accounting."""

    records: list[dict[str, Any]] = field(default_factory=_empty_records)
    files_read: int = 0
    malformed_lines: int = 0


def read_runtime_events(
    events_dir: Path,
    *,
    file_limit: int | None = None,
) -> RuntimeEventReadResult:
    """Return JSON object events from newest JSONL files."""
    if not events_dir.exists():
        return RuntimeEventReadResult()
    files = _event_files(events_dir, file_limit=file_limit)
    records: list[dict[str, Any]] = []
    malformed_lines = 0
    for event_file in files:
        read_result = _read_event_file(event_file)
        records.extend(read_result.records)
        malformed_lines += read_result.malformed_lines
    return RuntimeEventReadResult(
        records=records,
        files_read=len(files),
        malformed_lines=malformed_lines,
    )


def _event_files(events_dir: Path, *, file_limit: int | None) -> list[Path]:
    """Return newest event files in deterministic read order."""
    event_files = sorted(
        events_dir.glob("*.jsonl"),
        key=lambda event_file: (event_file.stat().st_mtime, event_file.name),
    )
    if file_limit is None:
        return event_files
    return event_files[-file_limit:]


def _read_event_file(event_file: Path) -> RuntimeEventReadResult:
    """Return JSON object events from one file."""
    records: list[dict[str, Any]] = []
    malformed_lines = 0
    try:
        lines = event_file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return RuntimeEventReadResult(malformed_lines=1)
    for line in lines:
        record = _parse_event_line(line)
        if record is None:
            malformed_lines += 1
        else:
            records.append(record)
    return RuntimeEventReadResult(records=records, malformed_lines=malformed_lines)


def _parse_event_line(line: str) -> dict[str, Any] | None:
    """Return one event object or None for malformed input."""
    if not line.strip():
        return None
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict):
        return payload
    return None
