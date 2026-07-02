"""Load DocSync trace graphs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from docsync.config.load import ConfigError, load_yaml_mapping
from docsync.core.models import (
    Claim,
    Severity,
    TraceDocument,
    TraceEvidence,
    TraceEvidenceAnchor,
    TraceGraph,
    TraceObject,
)


class TraceError(ValueError):
    """Raised when a DocSync trace file cannot be loaded."""


def load_trace(repo_root: Path, trace_path: Path | None = None) -> TraceGraph:
    """Load the human-authored DocSync trace graph."""
    resolved_root = repo_root.resolve()
    resolved_trace = _resolve_path(resolved_root, trace_path or Path(".docsync/trace.yml"))
    if not resolved_trace.exists():
        raise TraceError(f"DocSync trace not found: {resolved_trace}")
    try:
        payload = load_yaml_mapping(resolved_trace)
    except ConfigError as exc:
        raise TraceError(str(exc)) from exc
    version = payload.get("version")
    if version != 1:
        raise TraceError("DocSync trace version must be 1")
    _validate_schema_shape(payload)
    return TraceGraph(
        path=resolved_trace,
        documents=_load_documents(payload["documents"]),
        objects=_load_objects(payload["objects"]),
        claims=_load_claims(payload["claims"]),
        evidence=_load_evidence(payload["evidence"]),
    )


def _validate_schema_shape(payload: dict[str, Any]) -> None:
    required = ("documents", "objects", "claims", "evidence")
    missing = [key for key in required if key not in payload]
    if missing:
        joined = ", ".join(missing)
        raise TraceError(f"DocSync trace missing required top-level key(s): {joined}")
    for key in required:
        if not isinstance(payload[key], dict):
            raise TraceError(f"DocSync trace '{key}' must be a mapping")


def _load_documents(raw_documents: object) -> dict[str, TraceDocument]:
    documents = _mapping(raw_documents, "documents")
    loaded: dict[str, TraceDocument] = {}
    for document_id, raw_document in documents.items():
        payload = _mapping(raw_document, f"documents.{document_id}")
        loaded[document_id] = TraceDocument(
            document_id=document_id,
            path=Path(str(payload.get("path", ""))),
            title=_optional_string(payload.get("title")),
            audience=_optional_string(payload.get("audience")),
        )
    return loaded


def _load_objects(raw_objects: object) -> dict[str, TraceObject]:
    objects = _mapping(raw_objects, "objects")
    loaded: dict[str, TraceObject] = {}
    for object_id, raw_object in objects.items():
        payload = _mapping(raw_object, f"objects.{object_id}")
        heading = _mapping(payload.get("heading", {}), f"objects.{object_id}.heading")
        loaded[object_id] = TraceObject(
            object_id=object_id,
            document_id=str(payload.get("document", "")),
            kind=str(payload.get("kind", "")),
            path=Path(str(payload.get("path", ""))),
            marker=str(payload.get("marker", object_id)),
            heading_level=_optional_int(heading.get("level")),
            heading_text=_optional_string(heading.get("text")),
        )
    return loaded


def _load_claims(raw_claims: object) -> dict[str, Claim]:
    claims = _mapping(raw_claims, "claims")
    loaded: dict[str, Claim] = {}
    for claim_id, raw_claim in claims.items():
        payload = _mapping(raw_claim, f"claims.{claim_id}")
        loaded[claim_id] = Claim(
            claim_id=claim_id,
            object_id=str(payload.get("object", "")),
            text=str(payload.get("text", "")),
            severity=_severity(payload.get("severity", "medium")),
            evidence_ids=_string_tuple(payload.get("evidence", ())),
            acceptable_attestation_reasons=_string_tuple(
                _mapping(payload.get("review", {}), f"claims.{claim_id}.review").get(
                    "acceptable_attestation_reasons",
                    (),
                )
            ),
        )
    return loaded


def _load_evidence(raw_evidence: object) -> dict[str, TraceEvidence]:
    evidence = _mapping(raw_evidence, "evidence")
    loaded: dict[str, TraceEvidence] = {}
    for evidence_id, raw_item in evidence.items():
        payload = _mapping(raw_item, f"evidence.{evidence_id}")
        loaded[evidence_id] = TraceEvidence(
            evidence_id=evidence_id,
            evidence_type=str(payload.get("type", "")),
            description=_optional_string(payload.get("description")),
            anchors=_load_anchors(payload.get("anchors", ()), evidence_id),
        )
    return loaded


def _load_anchors(raw_anchors: object, evidence_id: str) -> tuple[TraceEvidenceAnchor, ...]:
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
                path=Path(str(payload.get("path", ""))),
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


def _resolve_path(repo_root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return repo_root / path
