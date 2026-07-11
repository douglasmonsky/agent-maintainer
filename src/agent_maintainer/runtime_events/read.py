"""Read local runtime event JSONL artifacts safely."""

from __future__ import annotations

import heapq
import json
import os
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agent_context.reading import file_safety
from agent_maintainer.core.structured_values import json_object

MAX_RUNTIME_EVENT_FILE_BYTES = file_safety.MAX_FILE_BYTES
DEFAULT_RUNTIME_EVENT_FILE_LIMIT = 32


def _empty_records() -> list[dict[str, Any]]:
    return []


def _empty_sources() -> list[RuntimeEventSource]:
    return []


@dataclass(frozen=True)
class RuntimeEventSource:
    """Source location for one runtime event JSONL record."""

    file: str
    line: int


@dataclass(frozen=True)
class RuntimeEventReadResult:
    """Runtime event read result with malformed-line accounting."""

    records: list[dict[str, Any]] = field(default_factory=_empty_records)
    sources: list[RuntimeEventSource] = field(default_factory=_empty_sources)
    files_read: int = 0
    malformed_lines: int = 0


def read_runtime_events(
    events_dir: Path,
    *,
    file_limit: int | None = None,
    workspace_root: Path | None = None,
    max_file_bytes: int = MAX_RUNTIME_EVENT_FILE_BYTES,
) -> RuntimeEventReadResult:
    """Return JSON object events from the newest JSONL files."""
    safe_events_dir = _safe_event_directory(events_dir, workspace_root=workspace_root)
    if safe_events_dir is None:
        return RuntimeEventReadResult()
    files = _event_files(
        safe_events_dir,
        file_limit=file_limit,
        max_file_bytes=max_file_bytes,
    )
    records: list[dict[str, Any]] = []
    sources: list[RuntimeEventSource] = []
    files_read = 0
    malformed_lines = 0
    for event_file in files:
        read_result = _read_event_file(
            event_file,
            workspace_root=workspace_root,
            max_file_bytes=max_file_bytes,
        )
        records.extend(read_result.records)
        sources.extend(read_result.sources)
        files_read += read_result.files_read
        malformed_lines += read_result.malformed_lines
    return RuntimeEventReadResult(
        records=records,
        sources=sources,
        files_read=files_read,
        malformed_lines=malformed_lines,
    )


def _safe_event_directory(
    events_dir: Path,
    *,
    workspace_root: Path | None,
) -> Path | None:
    """Return one safe event directory without following symlinks."""

    safe_dir = events_dir
    if workspace_root is not None:
        confined = file_safety.confined_path(events_dir, workspace_root=workspace_root)
        if isinstance(confined, file_safety.FileSafety):
            return None
        safe_dir = confined
    if (
        file_safety.refused_path(safe_dir)
        or file_safety.sensitive_path(safe_dir)
        or file_safety.has_symlink_parent(safe_dir)
    ):
        return None
    try:
        directory_stat = safe_dir.lstat()
    except OSError:
        return None
    if stat.S_ISLNK(directory_stat.st_mode) or not stat.S_ISDIR(directory_stat.st_mode):
        return None
    return safe_dir


def _event_files(
    events_dir: Path,
    *,
    file_limit: int | None,
    max_file_bytes: int,
) -> list[Path]:
    """Return newest event files in deterministic read order."""
    effective_limit = DEFAULT_RUNTIME_EVENT_FILE_LIMIT if file_limit is None else file_limit
    if effective_limit <= 0:
        return []
    try:
        event_files = _collect_event_files(
            events_dir,
            file_limit=effective_limit,
            max_file_bytes=max_file_bytes,
        )
    except OSError:
        return []
    return [item[2] for item in sorted(event_files)]


def _collect_event_files(
    events_dir: Path,
    *,
    file_limit: int,
    max_file_bytes: int,
) -> list[tuple[int, str, Path]]:
    """Collect a bounded heap of newest safe event files."""

    event_files: list[tuple[int, str, Path]] = []
    for event_file in events_dir.iterdir():
        if event_file.suffix != ".jsonl":
            continue
        metadata = _safe_event_metadata(event_file, max_file_bytes=max_file_bytes)
        if metadata is not None:
            heapq.heappush(
                event_files,
                (metadata.st_mtime_ns, event_file.name, event_file),
            )
            if len(event_files) > file_limit:
                heapq.heappop(event_files)
    return event_files


def _safe_event_metadata(event_file: Path, *, max_file_bytes: int) -> os.stat_result | None:
    """Return no-follow metadata for one eligible event file."""

    refusal = file_safety.inspect_path(event_file, max_bytes=max_file_bytes)
    if refusal is not None:
        return None
    try:
        metadata = event_file.lstat()
    except OSError:
        return None
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > max_file_bytes:
        return None
    return metadata


def _read_event_file(
    event_file: Path,
    *,
    workspace_root: Path | None,
    max_file_bytes: int,
) -> RuntimeEventReadResult:
    """Return JSON object events from one file."""
    safe_read = file_safety.read_bounded_utf8_file(
        event_file,
        workspace_root=workspace_root,
        max_bytes=max_file_bytes,
    )
    if not safe_read.safety.allowed or safe_read.text is None:
        return RuntimeEventReadResult()
    records: list[dict[str, Any]] = []
    sources: list[RuntimeEventSource] = []
    malformed_lines = 0
    for line_number, line in enumerate(safe_read.text.splitlines(), start=1):
        payload = _json_object(line)
        if payload is None:
            malformed_lines += 1
            continue
        records.append(payload)
        sources.append(RuntimeEventSource(file=event_file.name, line=line_number))
    return RuntimeEventReadResult(
        records=records,
        sources=sources,
        files_read=1,
        malformed_lines=malformed_lines,
    )


def _json_object(line: str) -> dict[str, Any] | None:
    """Return one event object or None for malformed input."""
    if not line.strip():
        return None
    try:
        payload: object = json.loads(line)
    except (json.JSONDecodeError, RecursionError):
        return None
    return json_object(payload)
