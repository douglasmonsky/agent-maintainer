"""Load and validate DocSync attestations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from docsync.attestations.files import load_attestation_files
from docsync.core.fingerprints import sha256_text
from docsync.core.models import Attestation, DocSyncIndex, Finding, LineSpan

if TYPE_CHECKING:
    from docsync.core.models import Claim


@dataclass(frozen=True)
class AttestationSet:
    """Loaded attestations and validation findings."""

    records: tuple[Attestation, ...]
    findings: tuple[Finding, ...]

    def has_valid_attestation(
        self,
        *,
        claim_id: str,
        evidence_id: str,
        current_fingerprint: str,
        current_anchor_fingerprints: tuple[str, ...] = (),
    ) -> bool:
        """Return whether an attestation matches the current evidence fingerprint."""

        return any(
            record.claim_id == claim_id
            and evidence_id in record.evidence_ids
            and (
                record.evidence_fingerprints.get(evidence_id) == current_fingerprint
                or (
                    bool(current_anchor_fingerprints)
                    and not record.evidence_anchor_fingerprints
                    and record.evidence_fingerprints.get(evidence_id)
                    == current_anchor_fingerprints[0]
                )
            )
            for record in self.records
        )


def load_attestations(index: DocSyncIndex) -> AttestationSet:
    """Load attestations from the configured attestation directory."""

    records, findings = load_attestation_files(index)
    findings.extend(_semantic_findings(index, records))
    return AttestationSet(records=tuple(records), findings=tuple(findings))


def _semantic_findings(index: DocSyncIndex, records: list[Attestation]) -> list[Finding]:
    return [finding for record in records for finding in _record_semantic_findings(index, record)]


def _record_semantic_findings(index: DocSyncIndex, record: Attestation) -> list[Finding]:
    claim = index.trace.claims.get(record.claim_id)
    if claim is None:
        return [
            _finding(
                "DS303",
                f"Attestation points to missing claim {record.claim_id}.",
                record.path,
            )
        ]
    findings = _audit_findings(record)
    findings.extend(_reason_findings(claim, record))
    findings.extend(_evidence_findings(index, record))
    return findings


def _audit_findings(record: Attestation) -> list[Finding]:
    findings: list[Finding] = []
    if not record.reviewer:
        findings.append(_finding("DS306", "Attestation reviewer is missing.", record.path))
    if record.expires_at and _expired(record.expires_at):
        findings.append(_finding("DS307", "Attestation has expired.", record.path))
    return findings


def _reason_findings(claim: Claim, record: Attestation) -> list[Finding]:
    if not claim.acceptable_attestation_reasons:
        return []
    if record.reason in claim.acceptable_attestation_reasons:
        return []
    return [
        _finding(
            "DS302",
            f"Attestation reason is not allowed: {record.reason}.",
            record.path,
        )
    ]


def _evidence_findings(index: DocSyncIndex, record: Attestation) -> list[Finding]:
    return [
        finding
        for evidence_id in record.evidence_ids
        for finding in _evidence_fingerprint_findings(index, record, evidence_id)
    ]


def _evidence_fingerprint_findings(
    index: DocSyncIndex,
    record: Attestation,
    evidence_id: str,
) -> list[Finding]:
    if evidence_id not in index.trace.evidence:
        return [
            _finding(
                "DS304",
                f"Attestation points to missing evidence {evidence_id}.",
                record.path,
            )
        ]
    current = _current_fingerprint(index, evidence_id)
    current_anchors = _current_anchor_fingerprints(index, evidence_id)
    if current is None:
        return []
    return _current_fingerprint_findings(record, evidence_id, current, current_anchors)


def _current_fingerprint_findings(
    record: Attestation,
    evidence_id: str,
    current: str,
    current_anchors: tuple[str, ...],
) -> list[Finding]:
    if record.evidence_fingerprints.get(evidence_id) == current:
        if record.evidence_anchor_fingerprints.get(evidence_id) == current_anchors:
            return []
        return [
            _finding(
                "DS308",
                f"Attestation is missing current anchor fingerprints for {evidence_id}.",
                record.path,
            )
        ]
    if _legacy_first_anchor_matches(record, evidence_id, current_anchors):
        return []
    return [
        _finding(
            "DS301",
            f"Attestation fingerprint is stale for {evidence_id}.",
            record.path,
        )
    ]


def _current_fingerprint(index: DocSyncIndex, evidence_id: str) -> str | None:
    anchors = index.evidence_anchors.get(evidence_id, ())
    if not anchors:
        return None
    return sha256_text("\n".join(anchor.content_hash for anchor in anchors))


def _current_anchor_fingerprints(
    index: DocSyncIndex,
    evidence_id: str,
) -> tuple[str, ...]:
    return tuple(anchor.content_hash for anchor in index.evidence_anchors.get(evidence_id, ()))


def _legacy_first_anchor_matches(
    record: Attestation,
    evidence_id: str,
    current_anchors: tuple[str, ...],
) -> bool:
    return (
        bool(current_anchors)
        and not record.evidence_anchor_fingerprints
        and record.evidence_fingerprints.get(evidence_id) == current_anchors[0]
    )


def _expired(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return True
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed < datetime.now(tz=UTC)


def _finding(code: str, message: str, path: Path) -> Finding:
    return Finding(
        code=code,
        severity="error",
        message=message,
        locations=(LineSpan(path=path, start_line=1, end_line=1),),
    )
