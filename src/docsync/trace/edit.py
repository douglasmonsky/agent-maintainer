"""Edit human-authored DocSync trace files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from docsync.config.io import read_bounded_text, write_text_file
from docsync.config.paths import (
    PathBoundaryError,
    resolve_input_within,
)
from docsync.trace.edit_payload import (
    TRACE_SECTIONS,
    load_payload,
    payload_section,
    reject_existing,
    write_payload,
)
from docsync.trace.errors import TraceEditError


@dataclass(frozen=True)
class DocumentEdit:
    """Inputs for adding or replacing one trace document."""

    path: Path
    title: str
    audience: str
    force: bool = False


@dataclass(frozen=True)
class ObjectEdit:
    """Inputs for adding or replacing one trace object."""

    document_id: str
    path: Path
    marker: str
    heading_level: int | None = None
    heading_text: str | None = None
    insert_marker: bool = False
    force: bool = False


@dataclass(frozen=True)
class EvidenceEdit:
    """Inputs for adding or replacing one trace evidence item."""

    path: Path
    evidence_type: str
    description: str | None = None
    insert_region: bool = False
    force: bool = False


@dataclass(frozen=True)
class ClaimEdit:
    """Inputs for adding or replacing one trace claim."""

    object_id: str
    text: str
    severity: str
    evidence_ids: tuple[str, ...]
    force: bool = False


def add_document(
    repo_root: Path,
    trace_path: Path | None,
    document_id: str,
    options: DocumentEdit,
) -> Path:
    """Add or replace one trace document entry."""
    resolved_trace, payload = load_payload(repo_root, trace_path)
    normalized_path, _ = _resolve_repo_input(
        repo_root,
        options.path,
        label="DocSync document path",
        allow_missing=True,
    )
    documents = payload_section(payload, "documents")
    reject_existing(documents, document_id, options.force)
    documents[document_id] = {
        "path": normalized_path.as_posix(),
        "title": options.title,
        "audience": options.audience,
    }
    write_payload(resolved_trace, payload)
    return resolved_trace


def add_object(
    repo_root: Path,
    trace_path: Path | None,
    object_id: str,
    options: ObjectEdit,
) -> Path:
    """Add or replace one trace object entry."""
    resolved_trace, payload = load_payload(repo_root, trace_path)
    normalized_path, full_path = _resolve_repo_input(
        repo_root,
        options.path,
        label="DocSync object path",
        allow_missing=not options.insert_marker,
    )
    objects = payload_section(payload, "objects")
    reject_existing(objects, object_id, options.force)
    entry: dict[str, Any] = {
        "document": options.document_id,
        "kind": "heading_section",
        "path": normalized_path.as_posix(),
        "marker": options.marker,
    }
    if options.heading_level is not None or options.heading_text is not None:
        heading: dict[str, Any] = {}
        if options.heading_level is not None:
            heading["level"] = options.heading_level
        if options.heading_text is not None:
            heading["text"] = options.heading_text
        entry["heading"] = heading
    objects[object_id] = entry
    if options.insert_marker:
        _insert_object_marker(full_path, options.marker, options.heading_text)
    write_payload(resolved_trace, payload)
    return resolved_trace


def add_evidence(
    repo_root: Path,
    trace_path: Path | None,
    evidence_id: str,
    options: EvidenceEdit,
) -> Path:
    """Add or replace one trace evidence entry."""
    resolved_trace, payload = load_payload(repo_root, trace_path)
    normalized_path, full_path = _resolve_repo_input(
        repo_root,
        options.path,
        label="DocSync evidence path",
        allow_missing=not options.insert_region,
    )
    evidence = payload_section(payload, "evidence")
    reject_existing(evidence, evidence_id, options.force)
    entry: dict[str, Any] = {
        "type": options.evidence_type,
        "anchors": [{"path": normalized_path.as_posix(), "mode": "explicit_region"}],
    }
    if options.description:
        entry["description"] = options.description
    evidence[evidence_id] = entry
    if options.insert_region:
        _append_evidence_region(full_path, evidence_id)
    write_payload(resolved_trace, payload)
    return resolved_trace


def add_claim(
    repo_root: Path,
    trace_path: Path | None,
    claim_id: str,
    options: ClaimEdit,
) -> Path:
    """Add or replace one trace claim entry."""
    resolved_trace, payload = load_payload(repo_root, trace_path)
    claims = payload_section(payload, "claims")
    reject_existing(claims, claim_id, options.force)
    claims[claim_id] = {
        "object": options.object_id,
        "text": options.text,
        "severity": options.severity,
        "evidence": list(options.evidence_ids),
    }
    write_payload(resolved_trace, payload)
    return resolved_trace


def trace_summary(repo_root: Path, trace_path: Path | None) -> dict[str, tuple[str, ...]]:
    """Return sorted trace IDs by section."""
    _, payload = load_payload(repo_root, trace_path)
    return {
        section: tuple(sorted(str(key) for key in payload_section(payload, section)))
        for section in TRACE_SECTIONS
    }


def _insert_object_marker(path: Path, marker: str, heading_text: str | None) -> None:
    marker_line = f"<!-- docsync:object {marker} -->"
    try:
        content = read_bounded_text(path, label="DocSync object-marker write target")
    except PathBoundaryError as exc:
        raise TraceEditError(str(exc)) from exc
    if marker_line in content:
        return
    lines = content.splitlines()
    index = _heading_index(lines, heading_text)
    lines.insert(index, marker_line)
    write_text_file(
        path,
        _joined_lines(lines),
        label="DocSync object-marker write target",
    )


def _heading_index(lines: list[str], heading_text: str | None) -> int:
    if heading_text is None:
        return 0
    suffix = f" {heading_text}"
    for index, line in enumerate(lines):
        if line.startswith("#") and line.rstrip("#").rstrip().endswith(suffix):
            return index
    return 0


def _append_evidence_region(path: Path, evidence_id: str) -> None:
    start = f"<!-- docsync:evidence.start {evidence_id} -->"
    try:
        content = read_bounded_text(path, label="DocSync evidence-region write target")
    except PathBoundaryError as exc:
        raise TraceEditError(str(exc)) from exc
    if start in content:
        return
    end = f"<!-- docsync:evidence.end {evidence_id} -->"
    suffix = f"\n{start}\n{end}\n"
    write_text_file(
        path,
        f"{content.rstrip()}{suffix}",
        label="DocSync evidence-region write target",
    )


def _joined_lines(lines: list[str]) -> str:
    return "{}\n".format("\n".join(lines))


def _resolve_repo_input(
    repo_root: Path,
    candidate: Path,
    *,
    label: str,
    allow_missing: bool,
) -> tuple[Path, Path]:
    resolved_root = repo_root.resolve()
    try:
        resolved = resolve_input_within(
            resolved_root,
            candidate,
            label=label,
            allow_missing=allow_missing,
        )
    except PathBoundaryError as exc:
        raise TraceEditError(str(exc)) from exc
    return resolved.relative_to(resolved_root), resolved
