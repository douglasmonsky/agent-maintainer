"""DocSync Markdown object region marker validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from docsync.core.models import Finding, LineSpan


@dataclass(frozen=True)
class Marker:
    """One hidden Markdown directive marker."""

    object_id: str
    line_number: int


def collect_markers(lines: list[str], directive: str) -> tuple[Marker, ...]:
    """Return all hidden Markdown markers for one exact directive."""
    markers: list[Marker] = []
    fence: str | None = None
    for line_number, line in enumerate(lines, start=1):
        fence = _updated_fence(line, fence)
        if fence is not None:
            continue
        object_id = marker_id(line, directive)
        if object_id is not None:
            markers.append(Marker(object_id=object_id, line_number=line_number))
    return tuple(markers)


def marker_id(line: str, directive: str) -> str | None:
    """Return object ID from a hidden Markdown directive marker."""
    stripped = line.strip()
    if not stripped.startswith("<!--") or not stripped.endswith("-->"):
        return None
    body = stripped[4:-3].strip()
    parts = body.split(maxsplit=1)
    if not parts or parts[0] != directive:
        return None
    if len(parts) == 1:
        return ""
    return parts[1].strip()


def _updated_fence(line: str, fence: str | None) -> str | None:
    stripped = line.strip()
    if fence is not None:
        return None if stripped.startswith(fence) else fence
    if stripped.startswith("```"):
        return "```"
    if stripped.startswith("~~~"):
        return "~~~"
    return None


def explicit_object_regions(
    path: Path,
    opening_markers: tuple[Marker, ...],
    end_markers: tuple[Marker, ...],
    *,
    require_object_end_markers: bool,
) -> tuple[dict[int, int], list[Finding]]:
    """Pair explicit object end markers with opening markers."""
    explicit_ends: dict[int, int] = {}
    findings: list[Finding] = []
    assigned_end_lines: set[int] = set()
    reported_end_lines: set[int] = set()

    for index, marker in enumerate(opening_markers):
        next_marker = opening_markers[index + 1] if index + 1 < len(opening_markers) else None
        markers_before_next = _end_markers_before_next(marker, next_marker, end_markers)
        if markers_before_next:
            first_end = markers_before_next[0]
            if first_end.object_id == marker.object_id:
                explicit_ends[marker.line_number] = first_end.line_number
                assigned_end_lines.add(first_end.line_number)
            else:
                findings.append(_mismatched_end_finding(path, marker, first_end))
                reported_end_lines.add(first_end.line_number)
            continue

        matching_later = _first_matching_end_after(marker, end_markers)
        if matching_later is not None and next_marker is not None:
            findings.append(
                _finding(
                    "DS113",
                    (
                        f"Object marker {next_marker.object_id} starts before "
                        f"{marker.object_id} closes."
                    ),
                    path,
                    next_marker.line_number,
                ),
            )
            continue

        if require_object_end_markers:
            findings.append(
                _finding(
                    "DS110",
                    f"Object marker {marker.object_id} has no explicit end marker.",
                    path,
                    marker.line_number,
                ),
            )

    findings.extend(
        _unassigned_end_marker_findings(
            path,
            opening_markers,
            end_markers,
            assigned_end_lines=assigned_end_lines,
            reported_end_lines=reported_end_lines,
        ),
    )
    return explicit_ends, findings


def _end_markers_before_next(
    marker: Marker,
    next_marker: Marker | None,
    end_markers: tuple[Marker, ...],
) -> tuple[Marker, ...]:
    """Return end markers between this object marker and the next object marker."""
    return tuple(
        end_marker
        for end_marker in end_markers
        if end_marker.line_number > marker.line_number
        and (next_marker is None or end_marker.line_number < next_marker.line_number)
    )


def _first_matching_end_after(marker: Marker, end_markers: tuple[Marker, ...]) -> Marker | None:
    """Return the first matching end marker after an object marker."""
    for end_marker in end_markers:
        if end_marker.object_id == marker.object_id and end_marker.line_number > marker.line_number:
            return end_marker
    return None


def _unassigned_end_marker_findings(
    path: Path,
    opening_markers: tuple[Marker, ...],
    end_markers: tuple[Marker, ...],
    *,
    assigned_end_lines: set[int],
    reported_end_lines: set[int],
) -> list[Finding]:
    """Return findings for end markers that did not close an object."""
    findings: list[Finding] = []
    for end_marker in end_markers:
        if end_marker.line_number in assigned_end_lines | reported_end_lines:
            continue
        previous = _previous_opening(end_marker, opening_markers)
        if previous is None:
            findings.append(
                _finding(
                    "DS112",
                    f"Object end marker {end_marker.object_id} has no opening marker.",
                    path,
                    end_marker.line_number,
                ),
            )
            continue
        if previous.object_id != end_marker.object_id:
            findings.append(_mismatched_end_finding(path, previous, end_marker))
            continue
        findings.append(
            _finding(
                "DS114",
                f"Object end marker {end_marker.object_id} appears after another object starts.",
                path,
                end_marker.line_number,
            ),
        )
    return findings


def _previous_opening(end_marker: Marker, opening_markers: tuple[Marker, ...]) -> Marker | None:
    """Return nearest opening marker before an end marker."""
    previous: Marker | None = None
    for marker in opening_markers:
        if marker.line_number >= end_marker.line_number:
            break
        previous = marker
    return previous


def _mismatched_end_finding(path: Path, opening: Marker, ending: Marker) -> Finding:
    """Return a mismatch finding for object open/end marker IDs."""
    return _finding(
        "DS111",
        (f"Object end marker {ending.object_id} does not match open object {opening.object_id}."),
        path,
        ending.line_number,
    )


def _finding(code: str, message: str, path: Path, line: int) -> Finding:
    """Return one Markdown object-region finding."""
    return Finding(
        code=code,
        severity="error",
        message=message,
        locations=(LineSpan(path=path, start_line=line, end_line=line),),
    )
