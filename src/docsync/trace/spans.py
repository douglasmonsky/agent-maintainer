"""Locate trace item spans in human-authored YAML text."""

from __future__ import annotations

from pathlib import Path

from docsync.core.models import LineSpan

TRACE_SECTION_NAMES = frozenset(("documents", "objects", "claims", "evidence"))


def trace_item_spans(text: str, *, span_path: Path) -> dict[tuple[str, str], LineSpan]:
    """Return line spans for every top-level trace item."""

    lines = text.splitlines()
    starts = _trace_item_starts(lines)
    return _trace_spans_from_starts(starts, len(lines), span_path)


def _trace_item_starts(lines: list[str]) -> list[tuple[str, str, int]]:
    starts: list[tuple[str, str, int]] = []
    current_section: str | None = None
    for line_number, line in enumerate(lines, start=1):
        section = _trace_section(line)
        if section is not None:
            current_section = section
            continue
        if current_section is not None and _is_trace_item_line(line):
            item_id = line.strip().split(":", 1)[0]
            starts.append((current_section, item_id, line_number))
    return starts


def _trace_section(line: str) -> str | None:
    stripped = line.strip()
    if line.startswith(" ") or not stripped.endswith(":"):
        return None
    section = stripped[:-1]
    if section in TRACE_SECTION_NAMES:
        return section
    return None


def _is_trace_item_line(line: str) -> bool:
    return line.startswith("  ") and not line.startswith("    ") and ":" in line.strip()


def _trace_spans_from_starts(
    starts: list[tuple[str, str, int]],
    line_count: int,
    span_path: Path,
) -> dict[tuple[str, str], LineSpan]:
    spans: dict[tuple[str, str], LineSpan] = {}
    for index, (section, item_id, start_line) in enumerate(starts):
        next_start = starts[index + 1][2] if index + 1 < len(starts) else line_count + 1
        spans[(section, item_id)] = LineSpan(
            path=span_path,
            start_line=start_line,
            end_line=next_start - 1,
        )
    return spans
