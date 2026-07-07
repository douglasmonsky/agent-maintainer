"""Agent-oriented DocSync review packets."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from docsync.core.models import CheckResult, EvidenceAnchor, LineSpan


def review_packet_for_result(result: CheckResult) -> dict[str, Any]:
    """Return a compact JSON-ready review packet."""
    return {
        "version": 1,
        "command": result.command,
        "base_ref": result.base_ref,
        "ok": result.ok,
        "findings": [finding.to_json() for finding in result.findings],
        "reviews": [_review_item(result, finding) for finding in result.findings],
    }


def review_prompt_for_result(result: CheckResult) -> str:
    """Return Markdown prompt for agent review."""
    base_ref = result.base_ref or "n/a"
    lines = [
        "# DocSync Review Packet",
        "",
        f"Command: `{result.command}`",
        f"Base ref: `{base_ref}`",
        "",
    ]
    if result.ok:
        lines.append("No DocSync findings require review.")
        return _lines_text(lines)
    for finding in result.findings:
        lines.extend([f"## {finding.code}", "", finding.message, ""])
        item = _review_item(result, finding)
        for claim in item["claims"]:
            lines.append(f"- Claim `{claim['id']}`: {claim['text']}")
        for action in item["suggested_actions"]:
            lines.append(f"- Action: {action}")
        for location in finding.locations:
            path = location.path.as_posix()
            lines.append(f"- `{path}:L{location.start_line}-L{location.end_line}`")
        if finding.related_claims:
            claims = ", ".join(finding.related_claims)
            lines.append(f"- Claims: `{claims}`")
        if finding.related_evidence:
            evidence = ", ".join(finding.related_evidence)
            lines.append(f"- Evidence: `{evidence}`")
        lines.append("")
    return "\n".join(lines)


def _lines_text(lines: list[str]) -> str:
    text = "\n".join(lines)
    return f"{text}\n"


def _review_item(result: CheckResult, finding: Any) -> dict[str, Any]:
    index = result.index
    item: dict[str, Any] = {
        "finding": finding.to_json(),
        "claims": [],
        "evidence": [],
        "doc_context": [],
        "suggested_actions": [],
    }
    if index is None:
        return item
    for claim_id in finding.related_claims:
        claim = index.trace.claims.get(claim_id)
        if claim is None:
            continue
        item["claims"].append(
            {
                "id": claim.claim_id,
                "text": claim.text,
                "content_hash": claim.content_hash,
                "doc_object": claim.object_id,
                "marker": claim.marker,
            }
        )
        doc_object = index.doc_objects.get(claim.object_id)
        if doc_object is not None:
            span = index.claim_spans.get(claim_id, doc_object.span)
            item["doc_context"].append(_snippet(index.config.repo_root, span))
        for evidence_id in claim.evidence_ids:
            for anchor in index.evidence_anchors.get(evidence_id, ()):
                item["evidence"].append(_evidence_snippet(index.config.repo_root, anchor))
        item["suggested_actions"].extend(_actions(claim.claim_id, claim.evidence_ids))
    return item


def _evidence_snippet(repo_root: Path, anchor: EvidenceAnchor) -> dict[str, Any]:
    payload = _snippet(repo_root, anchor.content_span)
    payload["id"] = anchor.evidence_id
    payload["content_hash"] = anchor.content_hash
    return payload


def _snippet(repo_root: Path, span: LineSpan) -> dict[str, Any]:
    path = repo_root / span.path
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    start = max(span.start_line, 1)
    end = min(span.end_line, len(lines))
    return {
        "path": span.path.as_posix(),
        "start_line": span.start_line,
        "end_line": span.end_line,
        "text": "\n".join(lines[start - 1 : end]),
    }


def _actions(claim_id: str, evidence_ids: tuple[str, ...]) -> list[str]:
    evidence_args = " ".join(f"--evidence {evidence_id}" for evidence_id in evidence_ids)
    return [
        "Update the linked documentation claim or claim marker span.",
        (
            "If the documentation remains accurate, run "
            f"`docsync attest {claim_id} {evidence_args} --reason <reason>`."
        ),
    ]
