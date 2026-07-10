"""Structural DocSync validation."""

from __future__ import annotations

from pathlib import Path

from docsync.config.load import ConfigError, load_config
from docsync.core.models import CheckResult, DocSyncConfig, Finding, LineSpan, TraceGraph
from docsync.indexer import resolve_index
from docsync.trace.load import TraceError, load_trace


def run_doctor(
    *,
    repo_root: Path,
    config_path: Path | None,
    trace_path: Path | None,
    command: str,
    base_ref: str | None,
) -> CheckResult:
    """Run structural validation for DocSync files."""
    resolved_root = repo_root.resolve()
    try:
        config = load_config(resolved_root, config_path)
    except ConfigError as exc:
        fallback = _fallback_config(resolved_root, config_path)
        return _error_result(
            command,
            resolved_root,
            fallback,
            _config_finding(str(exc), fallback.config_path),
            base_ref,
        )
    try:
        trace = load_trace(resolved_root, trace_path)
    except TraceError as exc:
        return _error_result(
            command,
            resolved_root,
            config,
            _trace_finding(str(exc), trace_path or config.trace_path),
            base_ref,
        )
    findings = tuple(_trace_findings(resolved_root, trace))
    index = None
    if not trace.is_empty:
        index = resolve_index(config, trace)
        findings = (*findings, *index.findings)
    return CheckResult(
        command=command,
        repo_root=resolved_root,
        config=config,
        findings=findings,
        base_ref=base_ref,
        index=index,
    )


def _trace_findings(repo_root: Path, trace: TraceGraph) -> list[Finding]:
    findings: list[Finding] = []
    if trace.is_empty:
        findings.append(
            Finding(
                code="DS000",
                severity="info",
                message="DocSync trace is empty or incomplete.",
                locations=(_line(trace.path),),
            )
        )
        return findings
    findings.extend(_document_findings(repo_root, trace))
    findings.extend(_object_findings(trace))
    findings.extend(_claim_findings(trace))
    findings.extend(_evidence_findings(trace))
    return findings


def _document_findings(repo_root: Path, trace: TraceGraph) -> list[Finding]:
    findings: list[Finding] = []
    for document in trace.documents.values():
        if not (repo_root / document.path).exists():
            findings.append(
                Finding(
                    code="DS000",
                    severity="error",
                    message=f"Document path does not exist: {document.path}",
                    locations=(document.trace_span or _line(trace.path),),
                )
            )
    return findings


def _object_findings(trace: TraceGraph) -> list[Finding]:
    findings: list[Finding] = []
    for doc_object in trace.objects.values():
        if doc_object.document_id not in trace.documents:
            findings.append(
                Finding(
                    code="DS000",
                    severity="error",
                    message=(
                        f"Doc object {doc_object.object_id} references missing "
                        f"document {doc_object.document_id}."
                    ),
                    locations=(doc_object.trace_span or _line(trace.path),),
                )
            )
    return findings


def _claim_findings(trace: TraceGraph) -> list[Finding]:
    findings: list[Finding] = []
    for claim in trace.claims.values():
        if claim.object_id not in trace.objects:
            findings.append(
                Finding(
                    code="DS203",
                    severity="error",
                    message=(
                        f"Claim {claim.claim_id} points to missing doc object {claim.object_id}."
                    ),
                    locations=(claim.trace_span or _line(trace.path),),
                    related_claims=(claim.claim_id,),
                )
            )
        if not claim.evidence_ids:
            findings.append(
                Finding(
                    code="DS205",
                    severity="error",
                    message=f"Claim {claim.claim_id} has no evidence.",
                    locations=(claim.trace_span or _line(trace.path),),
                    related_claims=(claim.claim_id,),
                )
            )
        findings.extend(_missing_claim_evidence_findings(trace, claim.claim_id))
    return findings


def _missing_claim_evidence_findings(
    trace: TraceGraph,
    claim_id: str,
) -> list[Finding]:
    claim = trace.claims[claim_id]
    return [
        Finding(
            code="DS204",
            severity="error",
            message=f"Claim {claim_id} points to missing evidence {evidence_id}.",
            locations=(claim.trace_span or _line(trace.path),),
            related_claims=(claim_id,),
            related_evidence=(evidence_id,),
        )
        for evidence_id in claim.evidence_ids
        if evidence_id not in trace.evidence
    ]


def _evidence_findings(trace: TraceGraph) -> list[Finding]:
    findings: list[Finding] = []
    for evidence in trace.evidence.values():
        if not evidence.anchors:
            findings.append(
                Finding(
                    code="DS006",
                    severity="error",
                    message=f"Evidence {evidence.evidence_id} has no anchors.",
                    locations=(evidence.trace_span or _line(trace.path),),
                    related_evidence=(evidence.evidence_id,),
                )
            )
    return findings


def _error_result(
    command: str,
    repo_root: Path,
    config: DocSyncConfig,
    finding: Finding,
    base_ref: str | None,
) -> CheckResult:
    return CheckResult(
        command=command,
        repo_root=repo_root,
        config=config,
        findings=(finding,),
        base_ref=base_ref,
        inputs_valid=False,
    )


def _fallback_config(repo_root: Path, config_path: Path | None) -> DocSyncConfig:
    config = config_path or repo_root / ".docsync" / "config.yml"
    docsync_out = repo_root / ".docsync" / "out"
    return DocSyncConfig(
        repo_root=repo_root,
        config_path=config,
        trace_path=repo_root / ".docsync" / "trace.yml",
        attestations_dir=repo_root / ".docsync" / "attestations",
        output_dir=docsync_out,
        index_json=docsync_out / "index.json",
        report_json=docsync_out / "report.json",
        review_packet_json=docsync_out / "review-packet.json",
        review_prompt_md=docsync_out / "review-prompt.md",
        object_marker="docsync:object",
        object_end_marker="docsync:object.end",
        require_object_end_markers=False,
        evidence_start_directive="docsync:evidence.start",
        evidence_end_directive="docsync:evidence.end",
    )


def _config_finding(message: str, path: Path) -> Finding:
    return Finding(
        code="DS000",
        severity="error",
        message=message,
        locations=(_line(path),),
    )


def _trace_finding(message: str, path: Path) -> Finding:
    return Finding(
        code="DS000",
        severity="error",
        message=message,
        locations=(_line(path),),
    )


def _line(path: Path) -> LineSpan:
    return LineSpan(path=path, start_line=1, end_line=1)
