"""Claim freshness checks for changed evidence."""

from __future__ import annotations

from docsync.attestations.load import AttestationSet
from docsync.core.models import DocSyncIndex, Finding, LineSpan


def changed_claim_findings(
    index: DocSyncIndex,
    changed_spans: tuple[LineSpan, ...],
    attestations: AttestationSet,
) -> tuple[Finding, ...]:
    """Return findings for claims whose evidence changed without review."""
    changed_evidence = _changed_evidence(index, changed_spans)
    changed_doc_objects = _changed_doc_objects(index, changed_spans)
    findings: list[Finding] = []
    for evidence_id in sorted(changed_evidence):
        for claim in index.trace.claims_citing(evidence_id):
            if claim.object_id in changed_doc_objects:
                continue
            if _attested(index, attestations, claim.claim_id, evidence_id):
                continue
            locations = _claim_locations(index, claim.object_id, evidence_id)
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
    return any(
        attestations.has_valid_attestation(
            claim_id=claim_id,
            evidence_id=evidence_id,
            current_fingerprint=anchor.content_hash,
        )
        for anchor in anchors
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


def _changed_doc_objects(
    index: DocSyncIndex,
    changed_spans: tuple[LineSpan, ...],
) -> set[str]:
    return {
        object_id
        for object_id, doc_object in index.doc_objects.items()
        if _any_overlap(doc_object.span, changed_spans)
    }


def _claim_locations(
    index: DocSyncIndex,
    object_id: str,
    evidence_id: str,
) -> tuple[LineSpan, ...]:
    locations: list[LineSpan] = []
    anchors = index.evidence_anchors.get(evidence_id, ())
    locations.extend(anchor.content_span for anchor in anchors)
    doc_object = index.doc_objects.get(object_id)
    if doc_object is not None:
        locations.append(doc_object.span)
    return tuple(locations)


def _any_overlap(span: LineSpan, changed_spans: tuple[LineSpan, ...]) -> bool:
    return any(span.overlaps(changed_span) for changed_span in changed_spans)
