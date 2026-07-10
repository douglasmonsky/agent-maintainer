"""Claim freshness checks for changed evidence."""

from __future__ import annotations

from docsync.attestations.load import AttestationSet
from docsync.core.fingerprints import sha256_text
from docsync.core.models import Claim, DocSyncIndex, Finding, LineSpan


def changed_claim_findings(
    index: DocSyncIndex,
    changed_spans: tuple[LineSpan, ...],
    attestations: AttestationSet,
) -> tuple[Finding, ...]:
    """Return findings for claims whose evidence changed without review."""
    changed_evidence = _changed_evidence(index, changed_spans)
    changed_claims = _changed_claims(index, changed_spans)
    findings: list[Finding] = []
    for evidence_id in sorted(changed_evidence):
        for claim in index.trace.claims_citing(evidence_id):
            if claim.claim_id in changed_claims:
                continue
            if _attested(index, attestations, claim.claim_id, evidence_id):
                continue
            locations = _claim_locations(index, claim.claim_id, claim.object_id, evidence_id)
            findings.append(
                Finding(
                    code="DS201",
                    severity=claim.severity,
                    message=(
                        f"Evidence {evidence_id} changed, but linked documentation "
                        f"object {claim.object_id} was not updated or attested."
                    ),
                    locations=locations,
                    related_claims=(claim.claim_id,),
                    related_evidence=(evidence_id,),
                )
            )
    return tuple(findings)


def _attested(
    index: DocSyncIndex,
    attestations: AttestationSet,
    claim_id: str,
    evidence_id: str,
) -> bool:
    anchors = index.evidence_anchors.get(evidence_id, ())
    anchor_fingerprints = tuple(anchor.content_hash for anchor in anchors)
    current_fingerprint = sha256_text("\n".join(anchor_fingerprints))
    return attestations.has_valid_attestation(
        claim_id=claim_id,
        evidence_id=evidence_id,
        current_fingerprint=current_fingerprint,
        current_anchor_fingerprints=anchor_fingerprints,
    )


def _changed_evidence(
    index: DocSyncIndex,
    changed_spans: tuple[LineSpan, ...],
) -> set[str]:
    changed: set[str] = set()
    for evidence_id, anchors in index.evidence_anchors.items():
        if any(_any_overlap(anchor.content_span, changed_spans) for anchor in anchors):
            changed.add(evidence_id)
    return changed


def _changed_claims(
    index: DocSyncIndex,
    changed_spans: tuple[LineSpan, ...],
) -> set[str]:
    changed: set[str] = set()
    for claim in index.trace.claims.values():
        if _claim_changed(index, claim, changed_spans):
            changed.add(claim.claim_id)
    return changed


def _claim_changed(
    index: DocSyncIndex,
    claim: Claim,
    changed_spans: tuple[LineSpan, ...],
) -> bool:
    if _optional_span_changed(claim.trace_span, changed_spans):
        return True
    if _optional_span_changed(index.claim_spans.get(claim.claim_id), changed_spans):
        return True
    if claim.marker is not None:
        return False
    doc_object = index.doc_objects.get(claim.object_id)
    return doc_object is not None and _any_overlap(doc_object.span, changed_spans)


def _optional_span_changed(
    span: LineSpan | None,
    changed_spans: tuple[LineSpan, ...],
) -> bool:
    return span is not None and _any_overlap(span, changed_spans)


def _claim_locations(
    index: DocSyncIndex,
    claim_id: str,
    object_id: str,
    evidence_id: str,
) -> tuple[LineSpan, ...]:
    locations: list[LineSpan] = []
    anchors = index.evidence_anchors.get(evidence_id, ())
    locations.extend(anchor.content_span for anchor in anchors)
    claim_span = index.claim_spans.get(claim_id)
    if claim_span is not None:
        locations.append(claim_span)
    doc_object = index.doc_objects.get(object_id)
    if doc_object is not None:
        locations.append(doc_object.span)
    return tuple(locations)


def _any_overlap(span: LineSpan, changed_spans: tuple[LineSpan, ...]) -> bool:
    return any(span.overlaps(changed_span) for changed_span in changed_spans)
