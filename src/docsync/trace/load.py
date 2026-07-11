"""Load DocSync trace graphs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from docsync.config.io import read_bounded_text
from docsync.config.load import ConfigError, parse_yaml_mapping
from docsync.config.paths import PathBoundaryError, resolve_input_within
from docsync.core.fingerprints import sha256_text
from docsync.core.models import (
    Claim,
    LineSpan,
    Severity,
    TraceDocument,
    TraceEvidence,
    TraceEvidenceAnchor,
    TraceGraph,
    TraceObject,
)
from docsync.trace.spans import trace_item_spans


class TraceError(ValueError):
    """Raised when a DocSync trace file cannot be loaded."""


MAX_TRACE_SOURCE_FILES = 512
MAX_TRACE_SOURCE_BYTES = 33_554_432


def load_trace(repo_root: Path, trace_path: Path | None = None) -> TraceGraph:
    """Load the human-authored DocSync trace graph."""
    resolved_root = repo_root.resolve()
    try:
        resolved_trace = resolve_input_within(
            resolved_root,
            trace_path or Path(".docsync/trace.yml"),
            label="DocSync trace path",
        )
    except PathBoundaryError as exc:
        raise TraceError(str(exc)) from exc
    trace_text, payload = _trace_payload(resolved_trace)
    version = payload.get("version")
    if version != 1:
        raise TraceError("DocSync trace version must be 1")
    _validate_schema_shape(payload)
    line_map = trace_item_spans(
        trace_text,
        span_path=_relative_path(resolved_root, resolved_trace),
    )
    graph = TraceGraph(
        path=resolved_trace,
        documents=_load_documents(resolved_root, payload["documents"], line_map),
        objects=_load_objects(resolved_root, payload["objects"], line_map),
        claims=_load_claims(payload["claims"], line_map),
        evidence=_load_evidence(resolved_root, payload["evidence"], line_map),
    )
    _validate_trace_source_budget(resolved_root, graph)
    return graph


def _trace_payload(path: Path) -> tuple[str, dict[str, Any]]:
    try:
        return _read_trace_payload(path)
    except (ConfigError, PathBoundaryError) as exc:
        raise TraceError(str(exc)) from exc


def _read_trace_payload(path: Path) -> tuple[str, dict[str, Any]]:
    text = read_bounded_text(path, label="DocSync trace path")
    return text, parse_yaml_mapping(text, path=path)


def _validate_schema_shape(payload: dict[str, Any]) -> None:
    required = ("documents", "objects", "claims", "evidence")
    missing = [key for key in required if key not in payload]
    if missing:
        joined = ", ".join(missing)
        raise TraceError(f"DocSync trace missing required top-level key(s): {joined}")
    for key in required:
        if not isinstance(payload[key], dict):
            raise TraceError(f"DocSync trace '{key}' must be a mapping")


def _load_documents(
    repo_root: Path,
    raw_documents: object,
    line_map: dict[tuple[str, str], LineSpan],
) -> dict[str, TraceDocument]:
    documents = _mapping(raw_documents, "documents")
    loaded: dict[str, TraceDocument] = {}
    for document_id, raw_document in documents.items():
        payload = _mapping(raw_document, f"documents.{document_id}")
        loaded[document_id] = TraceDocument(
            document_id=document_id,
            path=_repo_input_path(
                repo_root,
                payload.get("path", ""),
                label=f"documents.{document_id}.path",
            ),
            title=_optional_string(payload.get("title")),
            audience=_optional_string(payload.get("audience")),
            trace_span=line_map.get(("documents", document_id)),
        )
    return loaded


def _load_objects(
    repo_root: Path,
    raw_objects: object,
    line_map: dict[tuple[str, str], LineSpan],
) -> dict[str, TraceObject]:
    objects = _mapping(raw_objects, "objects")
    loaded: dict[str, TraceObject] = {}
    for object_id, raw_object in objects.items():
        payload = _mapping(raw_object, f"objects.{object_id}")
        heading = _mapping(payload.get("heading", {}), f"objects.{object_id}.heading")
        loaded[object_id] = TraceObject(
            object_id=object_id,
            document_id=str(payload.get("document", "")),
            kind=str(payload.get("kind", "")),
            path=_repo_input_path(
                repo_root,
                payload.get("path", ""),
                label=f"objects.{object_id}.path",
            ),
            marker=str(payload.get("marker", object_id)),
            heading_level=_optional_int(heading.get("level")),
            heading_text=_optional_string(heading.get("text")),
            trace_span=line_map.get(("objects", object_id)),
        )
    return loaded


def _load_claims(
    raw_claims: object,
    line_map: dict[tuple[str, str], LineSpan],
) -> dict[str, Claim]:
    claims = _mapping(raw_claims, "claims")
    loaded: dict[str, Claim] = {}
    for claim_id, raw_claim in claims.items():
        payload = _mapping(raw_claim, f"claims.{claim_id}")
        text = str(payload.get("text", ""))
        loaded[claim_id] = Claim(
            claim_id=claim_id,
            object_id=str(payload.get("object", "")),
            text=text,
            severity=_severity(payload.get("severity", "medium")),
            evidence_ids=_string_tuple(payload.get("evidence", ())),
            acceptable_attestation_reasons=_string_tuple(
                _mapping(payload.get("review", {}), f"claims.{claim_id}.review").get(
                    "acceptable_attestation_reasons",
                    (),
                )
            ),
            content_hash=sha256_text(text),
            marker=_optional_string(payload.get("marker")),
            trace_span=line_map.get(("claims", claim_id)),
        )
    return loaded


def _load_evidence(
    repo_root: Path,
    raw_evidence: object,
    line_map: dict[tuple[str, str], LineSpan],
) -> dict[str, TraceEvidence]:
    evidence = _mapping(raw_evidence, "evidence")
    loaded: dict[str, TraceEvidence] = {}
    for evidence_id, raw_item in evidence.items():
        payload = _mapping(raw_item, f"evidence.{evidence_id}")
        loaded[evidence_id] = TraceEvidence(
            evidence_id=evidence_id,
            evidence_type=str(payload.get("type", "")),
            description=_optional_string(payload.get("description")),
            anchors=_load_anchors(
                repo_root,
                payload.get("anchors", ()),
                evidence_id,
            ),
            trace_span=line_map.get(("evidence", evidence_id)),
        )
    return loaded


def _load_anchors(
    repo_root: Path,
    raw_anchors: object,
    evidence_id: str,
) -> tuple[TraceEvidenceAnchor, ...]:
    if raw_anchors is None:
        return ()
    if not isinstance(raw_anchors, list):
        raise TraceError(f"evidence.{evidence_id}.anchors must be a list")
    anchor_values = cast(list[object], raw_anchors)
    anchors: list[TraceEvidenceAnchor] = []
    for index, raw_anchor in enumerate(anchor_values):
        payload = _mapping(raw_anchor, f"evidence.{evidence_id}.anchors[{index}]")
        anchors.append(
            TraceEvidenceAnchor(
                path=_repo_input_path(
                    repo_root,
                    payload.get("path", ""),
                    label=f"evidence.{evidence_id}.anchors[{index}].path",
                ),
                mode=str(payload.get("mode", "")),
            )
        )
    return tuple(anchors)


def _mapping(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TraceError(f"DocSync trace '{name}' must be a mapping")
    return cast(dict[str, Any], value)


def _string_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, tuple):
        tuple_items = cast(tuple[object, ...], value)
        return tuple(str(item) for item in tuple_items)
    if not isinstance(value, list):
        raise TraceError("claim evidence must be a list")
    list_items = cast(list[object], value)
    return tuple(str(item) for item in list_items)


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int):
        raise TraceError("heading level must be an integer")
    return value


def _severity(value: object) -> Severity:
    severity = str(value)
    if severity in {"info", "low", "medium", "high", "critical", "error"}:
        return cast(Severity, severity)
    raise TraceError(f"Unsupported claim severity: {severity}")


def _relative_path(repo_root: Path, path: Path) -> Path:
    try:
        return path.relative_to(repo_root)
    except ValueError:
        return path


def _repo_input_path(repo_root: Path, value: object, *, label: str) -> Path:
    candidate = Path(str(value))
    try:
        resolved = resolve_input_within(
            repo_root,
            candidate,
            label=f"DocSync trace {label}",
            allow_missing=True,
        )
    except PathBoundaryError as exc:
        raise TraceError(str(exc)) from exc
    return resolved.relative_to(repo_root)


def _validate_trace_source_budget(repo_root: Path, graph: TraceGraph) -> None:
    """Bound the distinct repository files one trace can make DocSync inspect."""

    paths = {
        *(document.path for document in graph.documents.values()),
        *(doc_object.path for doc_object in graph.objects.values()),
        *(anchor.path for evidence in graph.evidence.values() for anchor in evidence.anchors),
    }
    if len(paths) > MAX_TRACE_SOURCE_FILES:
        raise TraceError(
            f"DocSync trace names {len(paths)} source files; limit is {MAX_TRACE_SOURCE_FILES}"
        )
    total_bytes = 0
    for relative_path in paths:
        full_path = repo_root / relative_path
        try:
            total_bytes += full_path.lstat().st_size
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise TraceError(f"Cannot inspect DocSync trace source: {relative_path}") from exc
        if total_bytes > MAX_TRACE_SOURCE_BYTES:
            raise TraceError(
                "DocSync trace source inputs exceed the "
                f"{MAX_TRACE_SOURCE_BYTES}-byte aggregate limit"
            )
