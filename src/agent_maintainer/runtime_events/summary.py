"""Summarize local runtime events without dumping raw JSONL."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from agent_maintainer.runtime_events.read import RuntimeEventReadResult

DEFAULT_RECENT_LIMIT = 8
DEFAULT_SLOW_LIMIT = 8


def _empty_event_counts() -> dict[str, int]:
    return {}


def _empty_rows() -> list[dict[str, object]]:
    return []


@dataclass(frozen=True)
class RuntimeEventSummary:
    """Compact event summary suitable for agent-facing output."""

    files_read: int
    total_events: int
    malformed_lines: int
    event_counts: dict[str, int] = field(default_factory=_empty_event_counts)
    failures: list[dict[str, object]] = field(default_factory=_empty_rows)
    slow_checks: list[dict[str, object]] = field(default_factory=_empty_rows)
    recent: list[dict[str, object]] = field(default_factory=_empty_rows)
    fresh_runs: int = 0
    reused_runs: int = 0
    hook_noops: int = 0

    def to_json(self) -> str:
        """Return deterministic JSON representation."""
        return json.dumps(self.to_payload(), indent=2, sort_keys=True)

    def to_payload(self) -> dict[str, object]:
        """Return JSON-serializable summary payload."""
        return {
            "files_read": self.files_read,
            "total_events": self.total_events,
            "malformed_lines": self.malformed_lines,
            "event_counts": self.event_counts,
            "fresh_runs": self.fresh_runs,
            "reused_runs": self.reused_runs,
            "hook_noops": self.hook_noops,
            "failures": self.failures,
            "slow_checks": self.slow_checks,
            "recent": self.recent,
        }


def summarize_runtime_events(
    read_result: RuntimeEventReadResult,
    *,
    recent_limit: int = DEFAULT_RECENT_LIMIT,
    slow_limit: int = DEFAULT_SLOW_LIMIT,
) -> RuntimeEventSummary:
    """Return compact summary from runtime event records."""
    records = read_result.records
    return RuntimeEventSummary(
        files_read=read_result.files_read,
        total_events=len(records),
        malformed_lines=read_result.malformed_lines,
        event_counts=_event_counts(records),
        failures=_failure_rows(records, recent_limit),
        slow_checks=_slow_check_rows(records, slow_limit),
        recent=_recent_rows(records, recent_limit),
        fresh_runs=_event_name_count(records, "verifier.fresh"),
        reused_runs=_event_name_count(records, "verifier.reused"),
        hook_noops=_hook_noop_count(records),
    )


def render_summary_text(summary: RuntimeEventSummary) -> str:
    """Render summary-first text for agents and humans."""
    if summary.total_events == 0:
        return "\n".join(
            (
                "Runtime Event Summary",
                "Result: no events found",
                f"Event files read: {summary.files_read}",
                f"Malformed lines: {summary.malformed_lines}",
            ),
        )
    lines = [
        "Runtime Event Summary",
        f"Events: {summary.total_events} across {summary.files_read} file(s)",
        f"Malformed lines: {summary.malformed_lines}",
        f"Verifier runs: fresh {summary.fresh_runs}, reused {summary.reused_runs}",
        f"Hook no-ops: {summary.hook_noops}",
        f"Failures/exceptions: {len(summary.failures)}",
    ]
    lines.extend(_render_rows("Top failures", summary.failures))
    lines.extend(_render_rows("Slow checks", summary.slow_checks))
    return "\n".join(lines)


def render_rows_text(title: str, rows: list[dict[str, object]]) -> str:
    """Render one row list with fallback."""
    lines = [title]
    lines.extend(_render_rows("", rows) or ["- none"])
    return "\n".join(line for line in lines if line)


def _event_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(record.get("event_name", "unknown")) for record in records)
    return dict(sorted(counts.items()))


def _failure_rows(
    records: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, object]]:
    failures = [_row(record) for record in records if _is_failure(record)]
    return failures[-limit:]


def _slow_check_rows(
    records: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, object]]:
    check_rows = [
        _row(record)
        for record in records
        if record.get("event_name") == "check.finished"
        and isinstance(record.get("duration_ms"), int)
    ]
    return sorted(
        check_rows,
        key=_duration_sort_value,
        reverse=True,
    )[:limit]


def _recent_rows(
    records: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, object]]:
    return [_row(record) for record in records[-limit:]]


def _row(record: dict[str, Any]) -> dict[str, object]:
    return {
        "event_name": str(record.get("event_name", "unknown")),
        "status": str(record.get("status", "")),
        "command": str(record.get("command", "")),
        "profile": str(record.get("profile", "")),
        "check": str(record.get("check", "")),
        "hook_id": str(record.get("hook_id", "")),
        "run_id": str(record.get("run_id", "")),
        "duration_ms": record.get("duration_ms", ""),
    }


def _is_failure(record: dict[str, Any]) -> bool:
    return (
        record.get("severity") == "error"
        or record.get("status") in {"fail", "exception"}
        or str(record.get("event_name", "")).endswith(".exception")
    )


def _event_name_count(records: list[dict[str, Any]], event_name: str) -> int:
    return sum(1 for record in records if record.get("event_name") == event_name)


def _hook_noop_count(records: list[dict[str, Any]]) -> int:
    return sum(
        1
        for record in records
        if record.get("event_name") == "hook.finished" and record.get("status") == "noop"
    )


def _render_rows(title: str, rows: list[dict[str, object]]) -> list[str]:
    if not rows:
        return []
    lines = [title] if title else []
    for row in rows:
        lines.append(f"- {_row_text(row)}")
    return lines


def _row_text(row: dict[str, object]) -> str:
    parts = [
        str(row.get("event_name", "unknown")),
        _optional_part("status", row.get("status")),
        _optional_part("command", row.get("command")),
        _optional_part("profile", row.get("profile")),
        _optional_part("check", row.get("check")),
        _optional_part("hook", row.get("hook_id")),
        _optional_part("run", row.get("run_id")),
        _optional_part("duration_ms", row.get("duration_ms")),
    ]
    return " ".join(part for part in parts if part)


def _duration_sort_value(row: dict[str, object]) -> int:
    """Return integer duration for sorting summary rows."""
    duration = row.get("duration_ms", 0)
    if isinstance(duration, int):
        return duration
    return 0


def _optional_part(label: str, value: object) -> str:
    if value in {"", None}:
        return ""
    return f"{label}={value}"
