"""Load and validate DocSync attestations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from docsync.config.load import ConfigError, load_yaml_mapping
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
    ) -> bool:
        """Return whether an attestation matches the current evidence fingerprint."""

        return any(
            record.claim_id == claim_id
            and evidence_id in record.evidence_ids
            and record.evidence_fingerprints.get(evidence_id) == current_fingerprint
            for record in self.records
        )


def load_attestations(index: DocSyncIndex) -> AttestationSet:
    """Load attestations from the configured attestation directory."""

    directory = index.config.attestations_dir
    if not directory.exists():
        return AttestationSet(records=(), findings=())
    records: list[Attestation] = []
    findings: list[Finding] = []
    seen_ids: set[str] = set()
    for path in sorted((*directory.glob("*.yml"), *directory.glob("*.yaml"))):
        loaded, load_findings = _load_attestation_file(path)
        findings.extend(load_findings)
        for record in loaded:
            if record.attestation_id in seen_ids:
                findings.append(
                    _finding(
                        "DS305",
                        f"Duplicate attestation {record.attestation_id}.",
                        record.path,
                    )
                )
                continue
            seen_ids.add(record.attestation_id)
            records.append(record)
    findings.extend(_semantic_findings(index, records))
    return AttestationSet(records=tuple(records), findings=tuple(findings))


def _load_attestation_file(path: Path) -> tuple[tuple[Attestation, ...], list[Finding]]:
    try:
        raw_records_value = load_yaml_mapping(path).get("attestations", [])
    except ConfigError as exc:
        return (), [_finding("DS301", str(exc), path)]
    if not isinstance(raw_records_value, list):
        return (), [_finding("DS301", "attestations must be a list", path)]
    raw_records = cast(list[object], raw_records_value)
    records: list[Attestation] = []
    findings: list[Finding] = []
    for index, raw_record in enumerate(raw_records):
        if not isinstance(raw_record, dict):
            findings.append(_finding("DS301", f"attestations[{index}] must be a mapping", path))
            continue
        record = _record(path, cast(dict[str, Any], raw_record))
        records.append(record)
    return tuple(records), findings


def _record(path: Path, payload: dict[str, Any]) -> Attestation:
    return Attestation(
        attestation_id=str(payload.get("id", "")),
        claim_id=str(payload.get("claim", "")),
        doc_object_id=str(payload.get("doc_object", "")),
        evidence_ids=_string_tuple(payload.get("evidence", ())),
        reason=str(payload.get("reason", "")),
        evidence_fingerprints=_fingerprint_map(payload.get("evidence_fingerprints", {})),
        path=path,
    )


def _fingerprint_map(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    mapping = cast(dict[object, object], value)
    return {str(key): str(item) for key, item in mapping.items()}


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
    findings = _reason_findings(claim, record)
    findings.extend(_evidence_findings(index, record))
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
    if current is None or record.evidence_fingerprints.get(evidence_id) == current:
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
    return anchors[0].content_hash


def _string_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        items = cast(list[object] | tuple[object, ...], value)
        return tuple(str(item) for item in items)
    return (str(value),)


def _finding(code: str, message: str, path: Path) -> Finding:
    return Finding(
        code=code,
        severity="error",
        message=message,
        locations=(LineSpan(path=path, start_line=1, end_line=1),),
    )
