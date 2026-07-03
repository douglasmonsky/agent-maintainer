"""Runtime event sinks."""

# pylint: disable=too-few-public-methods

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from typing import Final, Protocol

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.runtime_events.models import VALID_SEVERITIES, RuntimeEvent

SEVERITY_ORDER: Final = MappingProxyType(
    {
        "debug": 10,
        "info": 20,
        "warning": 30,
        "error": 40,
    }
)


class RuntimeEventSink(Protocol):
    """Sink accepts runtime events without affecting caller behavior."""

    def emit(self, event: RuntimeEvent) -> None:
        """Record one event."""


@dataclass
class NullRuntimeEventSink:
    """Runtime event sink used when events are disabled or unavailable."""

    last_error: str = ""

    def emit(self, event: RuntimeEvent) -> None:
        """Ignore one runtime event."""


def _empty_records() -> list[dict[str, object]]:
    return []


@dataclass
class InMemoryRuntimeEventSink:
    """Test sink keeps serialized runtime event records in memory."""

    records: list[dict[str, object]] = field(default_factory=_empty_records)

    def emit(self, event: RuntimeEvent) -> None:
        """Append one serialized event record."""
        self.records.append(event.to_record())


@dataclass
class JsonlRuntimeEventSink:
    """Best-effort JSONL runtime event writer."""

    path: Path
    history_limit: int
    min_level: str = "info"
    include_debug: bool = False
    last_error: str = ""

    @classmethod
    def create(
        cls,
        directory: Path,
        *,
        history_limit: int,
        min_level: str = "info",
        include_debug: bool = False,
        stream_id: str | None = None,
    ) -> JsonlRuntimeEventSink | NullRuntimeEventSink:
        """Create JSONL sink or no-op sink when local event storage is unavailable."""
        try:
            path = _prepare_event_path(directory, history_limit, stream_id)
        except OSError as exc:
            return NullRuntimeEventSink(last_error=str(exc))
        return cls(
            path=path,
            history_limit=history_limit,
            min_level=_normalized_level(min_level),
            include_debug=include_debug,
        )

    def emit(self, event: RuntimeEvent) -> None:
        """Append one event best-effort."""
        if not _should_emit(
            event,
            min_level=self.min_level,
            include_debug=self.include_debug,
        ):
            return
        try:
            self._write_record(event)
        except (OSError, TypeError, ValueError) as exc:
            self.last_error = str(exc)

    def _write_record(self, event: RuntimeEvent) -> None:
        """Append one JSONL event record."""
        record = event.to_record()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as event_file:
            event_file.write(_jsonl_line(record))


def make_runtime_event_sink(
    config: MaintainerConfig,
    *,
    stream_id: str | None = None,
) -> RuntimeEventSink:
    """Return configured runtime event sink."""
    if not config.runtime_events_enabled:
        return NullRuntimeEventSink()
    return JsonlRuntimeEventSink.create(
        Path(config.runtime_events_dir),
        history_limit=config.runtime_event_history_limit,
        min_level=config.runtime_event_level,
        include_debug=config.runtime_events_include_debug,
        stream_id=stream_id,
    )


def _prepare_event_path(
    directory: Path,
    history_limit: int,
    stream_id: str | None,
) -> Path:
    """Create event directory, prune old files, and return event path."""
    directory.mkdir(parents=True, exist_ok=True)
    _prune_event_files(directory, history_limit)
    return directory / _event_file_name(stream_id)


def _event_file_name(stream_id: str | None) -> str:
    """Return safe event stream file name."""
    return ".".join((stream_id or _default_stream_id(), "jsonl"))


def _jsonl_line(record: dict[str, object]) -> str:
    """Return compact JSONL line for one event record."""
    payload = json.dumps(record, sort_keys=True, separators=(",", ":"))
    return f"{payload}\n"


def _default_stream_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")


def _prune_event_files(directory: Path, history_limit: int) -> None:
    if history_limit <= 0:
        return
    event_files = sorted(
        directory.glob("*.jsonl"),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
    )
    for stale_file in event_files[:-history_limit]:
        stale_file.unlink(missing_ok=True)


def _normalized_level(level: str) -> str:
    normalized = level.lower().strip()
    if normalized in VALID_SEVERITIES:
        return normalized
    return "info"


def _should_emit(
    event: RuntimeEvent,
    *,
    min_level: str,
    include_debug: bool,
) -> bool:
    if event.severity not in SEVERITY_ORDER:
        raise ValueError(f"invalid runtime event severity: {event.severity}")
    if event.severity == "debug" and not include_debug:
        return False
    return SEVERITY_ORDER[event.severity] >= SEVERITY_ORDER[min_level]
