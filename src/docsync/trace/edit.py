"""Edit human-authored DocSync trace files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml

from docsync.config.load import ConfigError, load_yaml_mapping

TRACE_SECTIONS = ("documents", "objects", "claims", "evidence")


class TraceEditError(ValueError):
    """Raised when a trace edit cannot be applied safely."""


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
    resolved_trace, payload = _load_payload(repo_root, trace_path)
    documents = _section(payload, "documents")
    _reject_existing(documents, document_id, options.force)
    documents[document_id] = {
        "path": options.path.as_posix(),
        "title": options.title,
        "audience": options.audience,
    }
    _write_payload(resolved_trace, payload)
    return resolved_trace


def add_object(
    repo_root: Path,
    trace_path: Path | None,
    object_id: str,
    options: ObjectEdit,
) -> Path:
    """Add or replace one trace object entry."""
    resolved_trace, payload = _load_payload(repo_root, trace_path)
    objects = _section(payload, "objects")
    _reject_existing(objects, object_id, options.force)
    entry: dict[str, Any] = {
        "document": options.document_id,
        "kind": "heading_section",
        "path": options.path.as_posix(),
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
        _insert_object_marker(repo_root / options.path, options.marker, options.heading_text)
    _write_payload(resolved_trace, payload)
    return resolved_trace


def add_evidence(
    repo_root: Path,
    trace_path: Path | None,
    evidence_id: str,
    options: EvidenceEdit,
) -> Path:
    """Add or replace one trace evidence entry."""
    resolved_trace, payload = _load_payload(repo_root, trace_path)
    evidence = _section(payload, "evidence")
    _reject_existing(evidence, evidence_id, options.force)
    entry: dict[str, Any] = {
        "type": options.evidence_type,
        "anchors": [{"path": options.path.as_posix(), "mode": "explicit_region"}],
    }
    if options.description:
        entry["description"] = options.description
    evidence[evidence_id] = entry
    if options.insert_region:
        _append_evidence_region(repo_root / options.path, evidence_id)
    _write_payload(resolved_trace, payload)
    return resolved_trace


def add_claim(
    repo_root: Path,
    trace_path: Path | None,
    claim_id: str,
    options: ClaimEdit,
) -> Path:
    """Add or replace one trace claim entry."""
    resolved_trace, payload = _load_payload(repo_root, trace_path)
    claims = _section(payload, "claims")
    _reject_existing(claims, claim_id, options.force)
    claims[claim_id] = {
        "object": options.object_id,
        "text": options.text,
        "severity": options.severity,
        "evidence": list(options.evidence_ids),
    }
    _write_payload(resolved_trace, payload)
    return resolved_trace


def trace_summary(repo_root: Path, trace_path: Path | None) -> dict[str, tuple[str, ...]]:
    """Return sorted trace IDs by section."""
    _, payload = _load_payload(repo_root, trace_path)
    return {
        section: tuple(sorted(str(key) for key in _section(payload, section)))
        for section in TRACE_SECTIONS
    }


def _load_payload(
    repo_root: Path,
    trace_path: Path | None,
) -> tuple[Path, dict[str, Any]]:
    resolved_root = repo_root.resolve()
    resolved_trace = Path(".docsync/trace.yml") if trace_path is None else trace_path
    if not resolved_trace.is_absolute():
        resolved_trace = resolved_root / resolved_trace
    try:
        payload = load_yaml_mapping(resolved_trace)
    except ConfigError as exc:
        raise TraceEditError(str(exc)) from exc
    if payload.get("version") != 1:
        raise TraceEditError("DocSync trace version must be 1")
    for section in TRACE_SECTIONS:
        payload.setdefault(section, {})
        if not isinstance(payload[section], dict):
            raise TraceEditError(f"DocSync trace '{section}' must be a mapping")
    return resolved_trace, payload


def _section(payload: dict[str, Any], section: str) -> dict[str, Any]:
    value = payload[section]
    return cast(dict[str, Any], value)


def _reject_existing(section: dict[str, Any], item_id: str, force: bool) -> None:
    if force or item_id not in section:
        return
    raise TraceEditError(f"DocSync trace entry already exists: {item_id}")


def _write_payload(path: Path, payload: dict[str, Any]) -> None:
    ordered: dict[str, Any] = {"version": payload.get("version", 1)}
    for section in TRACE_SECTIONS:
        ordered[section] = {
            key: payload[section][key] for key in sorted(cast(dict[str, Any], payload[section]))
        }
    path.write_text(yaml.safe_dump(ordered, sort_keys=False), encoding="utf-8")


def _insert_object_marker(path: Path, marker: str, heading_text: str | None) -> None:
    if not path.exists():
        raise TraceEditError(f"Cannot insert object marker; path does not exist: {path}")
    marker_line = f"<!-- docsync:object {marker} -->"
    content = path.read_text(encoding="utf-8")
    if marker_line in content:
        return
    lines = content.splitlines()
    index = _heading_index(lines, heading_text)
    lines.insert(index, marker_line)
    path.write_text(_joined_lines(lines), encoding="utf-8")


def _heading_index(lines: list[str], heading_text: str | None) -> int:
    if heading_text is None:
        return 0
    suffix = f" {heading_text}"
    for index, line in enumerate(lines):
        if line.startswith("#") and line.rstrip("#").rstrip().endswith(suffix):
            return index
    return 0


def _append_evidence_region(path: Path, evidence_id: str) -> None:
    if not path.exists():
        raise TraceEditError(f"Cannot insert evidence region; path does not exist: {path}")
    start = f"<!-- docsync:evidence.start {evidence_id} -->"
    if start in path.read_text(encoding="utf-8"):
        return
    content = path.read_text(encoding="utf-8")
    end = f"<!-- docsync:evidence.end {evidence_id} -->"
    suffix = f"\n{start}\n{end}\n"
    path.write_text(f"{content.rstrip()}{suffix}", encoding="utf-8")


def _joined_lines(lines: list[str]) -> str:
    return "{}\n".format("\n".join(lines))
