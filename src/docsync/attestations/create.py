"""Create DocSync attestations."""

from __future__ import annotations

import subprocess  # nosec B404
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from docsync.config.io import write_text_file
from docsync.config.paths import PathBoundaryError, resolve_within
from docsync.core.fingerprints import sha256_text
from docsync.core.models import DocSyncIndex
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
    anchor_fingerprints = {
        evidence_id: tuple(anchor.content_hash for anchor in index.evidence_anchors[evidence_id])
        for evidence_id in evidence_ids
    }
    fingerprints = {
        evidence_id: _aggregate_fingerprint(values)
        for evidence_id, values in anchor_fingerprints.items()
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
                "evidence_anchor_fingerprints": {
                    evidence_id: list(values) for evidence_id, values in anchor_fingerprints.items()
                },
                "expires_at": None,
                "statement": "Reviewed changed evidence region. Documentation remains accurate.",
            }
        ],
    }
    return _write_attestation(index, attestation_id, payload)


def _write_attestation(
    index: DocSyncIndex,
    attestation_id: str,
    payload: dict[str, Any],
) -> Path:
    filename = f"{attestation_id}.yml"
    if Path(filename).name != filename:
        raise PathBoundaryError("DocSync attestation ID must not contain path separators")
    path = resolve_within(
        index.config.attestations_dir,
        Path(filename),
        label="DocSync attestation output",
    )
    index.config.attestations_dir.mkdir(parents=True, exist_ok=True)
    content = _yaml_module().safe_dump(payload, sort_keys=False)
    write_text_file(path, content, label="DocSync attestation output")
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


def _aggregate_fingerprint(values: tuple[str, ...]) -> str:
    return sha256_text("\n".join(values))


def _yaml_module() -> Any:
    return yaml
