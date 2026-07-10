"""Build resolved DocSync indexes."""

from __future__ import annotations

from pathlib import Path

from docsync.comments.scanner import scan_evidence_file
from docsync.config.io import read_bounded_text
from docsync.config.load import load_config
from docsync.config.paths import resolve_input_within
from docsync.core.models import (
    DocObject,
    DocSyncConfig,
    DocSyncIndex,
    EvidenceAnchor,
    Finding,
    LineSpan,
    TraceGraph,
)
from docsync.markdown.parser import parse_markdown_file
from docsync.trace.load import load_trace

EvidenceAnchorMap = dict[str, tuple[EvidenceAnchor, ...]]
ResolvedEvidenceAnchors = tuple[EvidenceAnchorMap, list[Finding]]


def build_docsync_index(
    repo_root: Path,
    *,
    config_path: Path | None = None,
    trace_path: Path | None = None,
) -> DocSyncIndex:
    """Build a resolved DocSync index from repository files."""
    config = load_config(repo_root, config_path)
    trace = load_trace(repo_root, trace_path)
    return resolve_index(config, trace)


def resolve_index(config: DocSyncConfig, trace: TraceGraph) -> DocSyncIndex:
    """Resolve trace graph objects against live repository files."""
    parsed_objects, doc_findings = _resolve_doc_objects(config, trace)
    evidence_anchors, evidence_findings = _resolve_evidence_anchors(config, trace)
    claim_spans, claim_findings = _resolve_claim_spans(config, trace, parsed_objects)
    findings = tuple(doc_findings + evidence_findings + claim_findings)
    return DocSyncIndex(
        config=config,
        trace=trace,
        doc_objects=parsed_objects,
        evidence_anchors=evidence_anchors,
        claim_spans=claim_spans,
        findings=findings,
    )


def _resolve_doc_objects(
    config: DocSyncConfig,
    trace: TraceGraph,
) -> tuple[dict[str, DocObject], list[Finding]]:
    parsed: dict[str, DocObject] = {}
    findings: list[Finding] = []
    parsed_paths: set[Path] = set()
    for document in trace.documents.values():
        if document.path in parsed_paths:
            continue
        parsed_paths.add(document.path)
        result = parse_markdown_file(
            config.repo_root,
            document.path,
            object_marker=config.object_marker,
            object_end_marker=config.object_end_marker,
            require_object_end_markers=config.require_object_end_markers,
        )
        parsed.update(result.objects)
        findings.extend(result.findings)
    findings.extend(_trace_object_findings(trace, parsed))
    findings.extend(_orphan_doc_object_findings(trace, parsed))
    return parsed, findings


def _trace_object_findings(
    trace: TraceGraph,
    parsed: dict[str, DocObject],
) -> list[Finding]:
    findings: list[Finding] = []
    for trace_object in trace.objects.values():
        parsed_object = parsed.get(trace_object.marker)
        if parsed_object is None:
            findings.append(
                Finding(
                    code="DS101",
                    severity="error",
                    message=f"Doc object marker missing: {trace_object.marker}",
                    locations=(_trace_line(trace),),
                )
            )
            continue
        if parsed_object.kind != trace_object.kind:
            findings.append(
                Finding(
                    code="DS108",
                    severity="error",
                    message=(
                        f"Doc object {trace_object.object_id} kind changed from "
                        f"{trace_object.kind} to {parsed_object.kind}."
                    ),
                    locations=(parsed_object.span,),
                )
            )
        if _title_changed(trace_object.heading_text, parsed_object.title):
            findings.append(
                Finding(
                    code="DS102",
                    severity="error",
                    message=(
                        f"Doc object {trace_object.object_id} title changed from "
                        f"{trace_object.heading_text!r} to {parsed_object.title!r}."
                    ),
                    locations=(parsed_object.span,),
                )
            )
        if _heading_level_changed(trace_object.heading_level, parsed_object.heading_level):
            findings.append(
                Finding(
                    code="DS103",
                    severity="error",
                    message=f"Doc object {trace_object.object_id} heading level changed.",
                    locations=(parsed_object.span,),
                )
            )
    return findings


def _orphan_doc_object_findings(
    trace: TraceGraph,
    parsed: dict[str, DocObject],
) -> list[Finding]:
    trace_markers = {trace_object.marker for trace_object in trace.objects.values()}
    return [
        Finding(
            code="DS109",
            severity="error",
            message=f"Markdown object marker is not in trace.yml: {object_id}",
            locations=(doc_object.span,),
        )
        for object_id, doc_object in sorted(parsed.items())
        if object_id not in trace_markers
    ]


def _resolve_evidence_anchors(
    config: DocSyncConfig,
    trace: TraceGraph,
) -> ResolvedEvidenceAnchors:
    by_evidence_id: dict[str, list[EvidenceAnchor]] = {}
    findings: list[Finding] = []
    for path in _evidence_paths(trace):
        result = scan_evidence_file(
            config.repo_root,
            path,
            start_directive=config.evidence_start_directive,
            end_directive=config.evidence_end_directive,
        )
        findings.extend(result.findings)
        for anchor in result.anchors:
            by_evidence_id.setdefault(anchor.evidence_id, []).append(anchor)
            if anchor.evidence_id not in trace.evidence:
                findings.append(
                    Finding(
                        code="DS005",
                        severity="error",
                        message=f"Evidence anchor not declared in trace.yml: {anchor.evidence_id}",
                        locations=(anchor.span,),
                        related_evidence=(anchor.evidence_id,),
                    )
                )
    evidence_anchors = {
        evidence_id: tuple(anchors)
        for evidence_id, anchors in sorted(by_evidence_id.items())
        if evidence_id in trace.evidence
    }
    findings.extend(_missing_evidence_anchor_findings(trace, evidence_anchors))
    return evidence_anchors, findings


def _resolve_claim_spans(
    config: DocSyncConfig,
    trace: TraceGraph,
    doc_objects: dict[str, DocObject],
) -> tuple[dict[str, LineSpan], list[Finding]]:
    spans: dict[str, LineSpan] = {}
    findings: list[Finding] = []
    lines_by_path: dict[Path, list[str] | None] = {}
    for claim in trace.claims.values():
        if claim.marker is None:
            continue
        doc_object = doc_objects.get(claim.object_id)
        if doc_object is None:
            continue
        if doc_object.path not in lines_by_path:
            lines_by_path[doc_object.path] = _claim_source_lines(
                config.repo_root,
                doc_object.path,
            )
        span = _claim_span(doc_object.path, claim.marker, lines_by_path[doc_object.path])
        if span is None:
            findings.append(
                Finding(
                    code="DS206",
                    severity="error",
                    message=f"Claim marker not found for {claim.claim_id}: {claim.marker}",
                    locations=(claim.trace_span or _trace_line(trace),),
                    related_claims=(claim.claim_id,),
                )
            )
            continue
        spans[claim.claim_id] = span
    return spans, findings


def _claim_source_lines(repo_root: Path, path: Path) -> list[str] | None:
    """Return one bounded claim source, cached by the caller."""

    full_path = resolve_input_within(
        repo_root,
        path,
        label="DocSync claim source",
        allow_missing=True,
    )
    if not full_path.exists():
        return None
    return read_bounded_text(full_path, label="DocSync claim source").splitlines()


def _claim_span(path: Path, marker: str, lines: list[str] | None) -> LineSpan | None:
    if lines is None:
        return None
    start = f"<!-- docsync:claim {marker} -->"
    end = f"<!-- docsync:claim.end {marker} -->"
    start_line: int | None = None
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped == start:
            start_line = line_number
            continue
        if stripped == end and start_line is not None:
            return LineSpan(path=path, start_line=start_line, end_line=line_number)
    return None


def _missing_evidence_anchor_findings(
    trace: TraceGraph,
    evidence_anchors: dict[str, tuple[EvidenceAnchor, ...]],
) -> list[Finding]:
    return [
        Finding(
            code="DS006",
            severity="error",
            message=f"Evidence {evidence_id} has no live anchor.",
            locations=(evidence.trace_span or _trace_line(trace),),
            related_evidence=(evidence_id,),
        )
        for evidence_id, evidence in sorted(trace.evidence.items())
        if evidence.anchors and not evidence_anchors.get(evidence_id)
    ]


def _evidence_paths(trace: TraceGraph) -> tuple[Path, ...]:
    paths = {
        anchor.path
        for evidence in trace.evidence.values()
        for anchor in evidence.anchors
        if anchor.mode == "explicit_region"
    }
    return tuple(sorted(paths))


def _title_changed(expected: str | None, actual: str | None) -> bool:
    return expected is not None and expected != actual


def _heading_level_changed(expected: int | None, actual: int | None) -> bool:
    return expected is not None and expected != actual


def _trace_line(trace: TraceGraph) -> LineSpan:
    return LineSpan(path=trace.path, start_line=1, end_line=1)
