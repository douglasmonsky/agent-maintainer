"""Create DocSync attestations."""

from __future__ import annotations

import subprocess  # nosec B404
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from docsync.indexer import build_docsync_index


def create_attestation_file(
    repo_root: Path,
    claim_id: str,
    evidence_ids: tuple[str, ...],
    reason: str,
) -> Path:
    """Create an attestation for current evidence fingerprints."""
    index = build_docsync_index(repo_root)
    claim = index.trace.claims[claim_id]
    fingerprints = {
        evidence_id: index.evidence_anchors[evidence_id][0].content_hash
        for evidence_id in evidence_ids
    }
    now = datetime.now(UTC).replace(microsecond=0)
    head = _git_head(repo_root)
    attestation_id = f"attest.{now.strftime('%Y%m%dT%H%M%SZ')}.{claim_id}.{head}"
    payload: dict[str, Any] = {
        "version": 1,
        "attestations": [
            {
                "id": attestation_id,
                "claim": claim_id,
                "doc_object": claim.object_id,
                "evidence": list(evidence_ids),
                "reason": reason,
                "reviewer": "agent",
                "reviewed_at": now.isoformat().replace("+00:00", "Z"),
                "base": "HEAD",
                "head": head,
                "evidence_fingerprints": fingerprints,
                "statement": "Reviewed changed evidence region. Documentation remains accurate.",
            }
        ],
    }
    index.config.attestations_dir.mkdir(parents=True, exist_ok=True)
    path = index.config.attestations_dir / f"{attestation_id}.yml"
    with path.open("w", encoding="utf-8") as handle:
        _yaml_module().safe_dump(payload, handle, sort_keys=False)
    return path


def _git_head(repo_root: Path) -> str:
    completed = subprocess.run(  # nosec B603
        ("git", "rev-parse", "--short", "HEAD"),
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip() or "working-tree"


def _yaml_module() -> Any:
    return yaml
