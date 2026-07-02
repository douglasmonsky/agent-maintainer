"""Core DocSync models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

Severity = Literal["info", "low", "medium", "high", "critical", "error"]


@dataclass(frozen=True)
class LineSpan:
    """Inclusive line span in a repository file."""

    path: Path
    start_line: int
    end_line: int
    inclusive: bool = True

    def overlaps(self, other: LineSpan) -> bool:
        """Return whether two spans overlap in the same file."""
        if self.path != other.path:
            return False
        return self.start_line <= other.end_line and other.start_line <= self.end_line

    def to_json(self) -> dict[str, Any]:
        """Return JSON-ready line span."""
        return {
            "path": self.path.as_posix(),
            "start_line": self.start_line,
            "end_line": self.end_line,
            "inclusive": self.inclusive,
        }


@dataclass(frozen=True)
class Finding:
    """DocSync check finding."""

    code: str
    severity: Severity
    message: str
    locations: tuple[LineSpan, ...] = ()
    related_claims: tuple[str, ...] = ()
    related_evidence: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        """Return JSON-ready finding."""
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "locations": [location.to_json() for location in self.locations],
            "related_claims": list(self.related_claims),
            "related_evidence": list(self.related_evidence),
        }


@dataclass(frozen=True)
class DocSyncConfig:
    """Resolved DocSync configuration."""

    repo_root: Path
    config_path: Path
    trace_path: Path
    attestations_dir: Path
    index_json: Path
    report_json: Path
    review_packet_json: Path
    review_prompt_md: Path
    object_marker: str
    evidence_start_directive: str
    evidence_end_directive: str


@dataclass(frozen=True)
class TraceDocument:
    """Human-authored document registered in trace.yml."""

    document_id: str
    path: Path
    title: str | None
    audience: str | None

    def to_json(self) -> dict[str, Any]:
        """Return JSON-ready trace document metadata."""
        return {
            "document_id": self.document_id,
            "path": self.path.as_posix(),
            "title": self.title,
            "audience": self.audience,
        }


@dataclass(frozen=True)
class TraceObject:
    """Documentation object registered in trace.yml."""

    object_id: str
    document_id: str
    kind: str
    path: Path
    marker: str
    heading_level: int | None = None
    heading_text: str | None = None


@dataclass(frozen=True)
class Claim:
    """Documentation claim linked to evidence objects."""

    claim_id: str
    object_id: str
    text: str
    severity: Severity
    evidence_ids: tuple[str, ...]
    acceptable_attestation_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class TraceEvidenceAnchor:
    """Evidence anchor declared in trace.yml."""

    path: Path
    mode: str


@dataclass(frozen=True)
class TraceEvidence:
    """Evidence object registered in trace.yml."""

    evidence_id: str
    evidence_type: str
    description: str | None
    anchors: tuple[TraceEvidenceAnchor, ...]


@dataclass(frozen=True)
class TraceGraph:
    """Loaded DocSync trace graph."""

    path: Path
    documents: dict[str, TraceDocument]
    objects: dict[str, TraceObject]
    claims: dict[str, Claim]
    evidence: dict[str, TraceEvidence]

    @property
    def is_empty(self) -> bool:
        """Return whether the trace graph has no user-authored graph nodes."""
        return not any((self.documents, self.objects, self.claims, self.evidence))

    def claims_citing(self, evidence_id: str) -> tuple[Claim, ...]:
        """Return claims that cite an evidence object."""
        return tuple(claim for claim in self.claims.values() if evidence_id in claim.evidence_ids)


@dataclass(frozen=True)
class EvidenceAnchor:
    """Resolved evidence anchor from source comments."""

    evidence_id: str
    path: Path
    span: LineSpan
    content_span: LineSpan
    content_hash: str

    def to_json(self) -> dict[str, Any]:
        """Return JSON-ready evidence anchor."""
        return {
            "evidence_id": self.evidence_id,
            "path": self.path.as_posix(),
            "span": self.span.to_json(),
            "content_span": self.content_span.to_json(),
            "content_hash": self.content_hash,
        }


@dataclass(frozen=True)
class DocObject:
    """Resolved Markdown documentation object."""

    object_id: str
    path: Path
    kind: str
    marker_line: int
    span: LineSpan
    title: str | None
    content_hash: str
    heading_line: int | None = None
    heading_level: int | None = None
    language: str | None = None

    def to_json(self) -> dict[str, Any]:
        """Return JSON-ready documentation object."""
        return {
            "object_id": self.object_id,
            "path": self.path.as_posix(),
            "kind": self.kind,
            "marker_line": self.marker_line,
            "span": self.span.to_json(),
            "title": self.title,
            "content_hash": self.content_hash,
            "heading_line": self.heading_line,
            "heading_level": self.heading_level,
            "language": self.language,
        }


@dataclass(frozen=True)
class DocSyncIndex:
    """Resolved DocSync index."""

    config: DocSyncConfig
    trace: TraceGraph
    doc_objects: dict[str, DocObject]
    evidence_anchors: dict[str, tuple[EvidenceAnchor, ...]]
    findings: tuple[Finding, ...] = ()

    @property
    def output_path(self) -> Path:
        """Return configured index output path."""
        return self.config.index_json

    def to_json(self) -> dict[str, Any]:
        """Return deterministic JSON-ready index payload."""
        return {
            "version": 1,
            "documents": {
                key: value.to_json() for key, value in sorted(self.trace.documents.items())
            },
            "doc_objects": {
                key: value.to_json() for key, value in sorted(self.doc_objects.items())
            },
            "evidence": {
                key: {
                    "type": self.trace.evidence[key].evidence_type,
                    "description": self.trace.evidence[key].description,
                    "anchors": [anchor.to_json() for anchor in anchors],
                }
                for key, anchors in sorted(self.evidence_anchors.items())
            },
            "claims": {
                key: {
                    "object": value.object_id,
                    "text": value.text,
                    "severity": value.severity,
                    "evidence": list(value.evidence_ids),
                }
                for key, value in sorted(self.trace.claims.items())
            },
            "findings": [finding.to_json() for finding in self.findings],
        }


@dataclass(frozen=True)
class Attestation:
    """Structured reviewed-but-unchanged claim attestation."""

    attestation_id: str
    claim_id: str
    doc_object_id: str
    evidence_ids: tuple[str, ...]
    reason: str
    evidence_fingerprints: dict[str, str]
    path: Path

    def to_json(self) -> dict[str, Any]:
        """Return JSON-ready attestation metadata."""
        return {
            "id": self.attestation_id,
            "claim": self.claim_id,
            "doc_object": self.doc_object_id,
            "evidence": list(self.evidence_ids),
            "reason": self.reason,
            "evidence_fingerprints": dict(sorted(self.evidence_fingerprints.items())),
            "path": self.path.as_posix(),
        }


@dataclass(frozen=True)
class CheckResult:
    """Result from a DocSync check command."""

    command: str
    repo_root: Path
    config: DocSyncConfig
    findings: tuple[Finding, ...]
    base_ref: str | None = None
    index: DocSyncIndex | None = None

    @property
    def ok(self) -> bool:
        """Return whether no findings were emitted."""
        return not self.findings

    def to_json(self) -> dict[str, Any]:
        """Return JSON-ready check result."""
        return {
            "command": self.command,
            "repo_root": self.repo_root.as_posix(),
            "base_ref": self.base_ref,
            "ok": self.ok,
            "findings": [finding.to_json() for finding in self.findings],
        }


IndexResult = DocSyncIndex
