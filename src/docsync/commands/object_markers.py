"""DocSync object marker repair commands."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from docsync.config.load import load_config
from docsync.markdown.object_regions import collect_markers
from docsync.markdown.parser import parse_markdown_file
from docsync.trace.load import load_trace


@dataclass(frozen=True)
class ObjectEndMarkerInsertion:
    """One planned object end-marker insertion."""

    path: Path
    object_id: str
    line_number: int


@dataclass(frozen=True)
class ObjectEndMarkerRepairResult:
    """Result of planning or applying object end-marker repairs."""

    insertions: tuple[ObjectEndMarkerInsertion, ...]
    wrote: bool


def repair_object_end_markers_main_from_args(args: argparse.Namespace) -> int:
    """Insert explicit DocSync object end markers where missing."""
    result = repair_object_end_markers(
        args.repo_root.resolve(),
        config_path=args.config,
        trace_path=args.trace,
        write=args.write,
    )
    if not result.insertions:
        print("DocSync object end markers are current.")
        return 0

    verb = "Inserted" if result.wrote else "Would insert"
    print(f"{verb} {len(result.insertions)} DocSync object end marker(s):")
    for insertion in result.insertions:
        print(f"- {insertion.path}:{insertion.line_number} {insertion.object_id}")
    if not result.wrote:
        print("Run again with --write to apply these repairs.")
    return 0


def repair_object_end_markers(
    repo_root: Path,
    *,
    config_path: Path | None = None,
    trace_path: Path | None = None,
    write: bool = False,
) -> ObjectEndMarkerRepairResult:
    """Plan or apply explicit object end-marker insertions."""
    config = load_config(repo_root, config_path)
    trace = load_trace(repo_root, trace_path or config.trace_path)
    insertions_by_path: dict[Path, list[ObjectEndMarkerInsertion]] = {}
    for document in trace.documents.values():
        path = document.path
        full_path = repo_root / path
        if not full_path.exists():
            continue
        lines = full_path.read_text(encoding="utf-8").splitlines()
        result = parse_markdown_file(
            repo_root,
            path,
            object_marker=config.object_marker,
            object_end_marker=config.object_end_marker,
            require_object_end_markers=False,
        )
        for doc_object in result.objects.values():
            next_marker_line = _next_object_marker_line(
                lines,
                doc_object.marker_line,
                config.object_marker,
            )
            if _has_end_marker_before_next_object(
                lines,
                doc_object.marker_line,
                doc_object.object_id,
                object_marker=config.object_marker,
                object_end_marker=config.object_end_marker,
            ):
                continue
            insertions_by_path.setdefault(path, []).append(
                ObjectEndMarkerInsertion(
                    path=path,
                    object_id=doc_object.object_id,
                    line_number=min(doc_object.span.end_line + 1, next_marker_line),
                ),
            )

    insertions = tuple(
        insertion
        for path in sorted(insertions_by_path)
        for insertion in sorted(
            insertions_by_path[path],
            key=lambda item: item.line_number,
        )
    )
    if write:
        _apply_insertions(repo_root, config.object_end_marker, insertions_by_path)
    return ObjectEndMarkerRepairResult(insertions=insertions, wrote=write)


def _has_end_marker_before_next_object(
    lines: list[str],
    marker_line: int,
    object_id: str,
    *,
    object_marker: str,
    object_end_marker: str,
) -> bool:
    end_marker = _marker_text(object_end_marker, object_id)
    stop_line = _next_object_marker_line(lines, marker_line, object_marker)
    for line_number in range(marker_line + 1, stop_line):
        if lines[line_number - 1].strip() == end_marker:
            return True
    return False


def _next_object_marker_line(lines: list[str], marker_line: int, object_marker: str) -> int:
    for marker in collect_markers(lines, object_marker):
        if marker.line_number > marker_line:
            return marker.line_number
    return len(lines) + 1


def _apply_insertions(
    repo_root: Path,
    object_end_marker: str,
    insertions_by_path: dict[Path, list[ObjectEndMarkerInsertion]],
) -> None:
    for path, insertions in insertions_by_path.items():
        full_path = repo_root / path
        lines = full_path.read_text(encoding="utf-8").splitlines()
        for insertion in sorted(insertions, key=lambda item: item.line_number, reverse=True):
            lines.insert(
                insertion.line_number - 1,
                _marker_text(object_end_marker, insertion.object_id),
            )
        content = "\n".join(lines)
        full_path.write_text(f"{content}\n", encoding="utf-8")


def _marker_text(directive: str, object_id: str) -> str:
    return f"<!-- {directive} {object_id} -->"
