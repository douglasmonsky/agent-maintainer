"""Tests for DocSync changed-claim checks."""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

from docsync.api import (
    CheckOptions,
    IndexOptions,
    build_index,
    check_repo,
    create_attestation,
    create_review_packet,
)
from docsync.attestations.load import load_attestations
from docsync.config.defaults import DEFAULT_CONFIG_TEXT
from docsync.core.fingerprints import sha256_text
from docsync.reports.review_packet import review_prompt_for_result
from docsync.reports.sarif import sarif_payload

CHANGED_EVIDENCE_LINE = 2
MULTI_ANCHOR_COUNT = 2


def test_check_reports_changed_evidence_without_doc_update(tmp_path: Path) -> None:
    """Changed evidence invalidates claims until docs are reviewed."""
    _write_repo(tmp_path)
    _commit_all(tmp_path)
    _replace(tmp_path / "src.py", "Demo behavior.", "Changed behavior.")

    result = check_repo(CheckOptions(repo_root=tmp_path, base_ref="HEAD"))

    assert [finding.code for finding in result.findings] == ["DS201"]
    assert result.findings[0].related_claims == ("claim.demo",)


def test_check_accepts_changed_evidence_with_doc_update(tmp_path: Path) -> None:
    """Updating linked documentation satisfies changed evidence review."""
    _write_repo(tmp_path)
    _commit_all(tmp_path)
    _replace(tmp_path / "src.py", "Demo behavior.", "Changed behavior.")
    _replace(tmp_path / "README.md", "Demo claim.", "Changed claim.")

    result = check_repo(CheckOptions(repo_root=tmp_path, base_ref="HEAD"))

    assert result.ok


def test_check_accepts_linked_object_update_when_claim_has_no_marker(tmp_path: Path) -> None:
    """Claims without precise markers fall back to their linked object span."""
    _write_repo(tmp_path)
    _replace(tmp_path / ".docsync" / "trace.yml", "    marker: claim.demo\n", "")
    _commit_all(tmp_path)
    _replace(tmp_path / "src.py", "Demo behavior.", "Changed behavior.")
    _replace(tmp_path / "README.md", "Demo claim.", "Changed claim.")

    result = check_repo(CheckOptions(repo_root=tmp_path, base_ref="HEAD"))

    assert result.ok


def test_check_rejects_unrelated_doc_object_update(tmp_path: Path) -> None:
    """Unrelated object edits do not satisfy changed evidence review."""
    _write_repo(tmp_path)
    _commit_all(tmp_path)
    _replace(tmp_path / "src.py", "Demo behavior.", "Changed behavior.")
    _replace(
        tmp_path / "README.md",
        "<!-- docsync:object.end docs.readme.demo -->",
        "Unrelated note.\n<!-- docsync:object.end docs.readme.demo -->",
    )

    result = check_repo(CheckOptions(repo_root=tmp_path, base_ref="HEAD"))

    assert [finding.code for finding in result.findings] == ["DS201"]


def test_check_accepts_changed_trace_claim_text(tmp_path: Path) -> None:
    """Trace claim text edits satisfy changed evidence review."""
    _write_repo(tmp_path)
    _commit_all(tmp_path)
    _replace(tmp_path / "src.py", "Demo behavior.", "Changed behavior.")
    _replace(tmp_path / ".docsync" / "trace.yml", "text: Demo claim.", "text: Changed claim.")

    result = check_repo(CheckOptions(repo_root=tmp_path, base_ref="HEAD"))

    assert result.ok


def test_check_accepts_changed_evidence_with_attestation(tmp_path: Path) -> None:
    """A valid current attestation satisfies changed evidence review."""
    _write_repo(tmp_path)
    _commit_all(tmp_path)
    _replace(tmp_path / "src.py", "Demo behavior.", "Changed behavior.")

    create_attestation(
        tmp_path,
        "claim.demo",
        ("evidence.demo",),
        "internal_refactor_only",
    )
    result = check_repo(CheckOptions(repo_root=tmp_path, base_ref="HEAD"))

    assert result.ok


def test_check_default_base_ref_falls_back_to_head(tmp_path: Path) -> None:
    """Default check works in repos without origin/main."""
    _write_repo(tmp_path)
    _commit_all(tmp_path)
    _replace(tmp_path / "src.py", "Demo behavior.", "Changed behavior.")

    result = check_repo(CheckOptions(repo_root=tmp_path))

    assert [finding.code for finding in result.findings] == ["DS201"]


def test_review_packet_includes_claim_evidence_and_actions(tmp_path: Path) -> None:
    """Review packet gives agents enough context to resolve a finding."""
    _write_repo(tmp_path)
    _commit_all(tmp_path)
    _replace(tmp_path / "src.py", "Demo behavior.", "Changed behavior.")

    result = check_repo(CheckOptions(repo_root=tmp_path, base_ref="HEAD"))
    packet = create_review_packet(result)
    review = packet["reviews"][0]

    assert review["finding"]["code"] == "DS201"
    assert review["claims"][0]["id"] == "claim.demo"
    assert review["claims"][0]["text"] == "Demo claim."
    assert review["claims"][0]["doc_object"] == "docs.readme.demo"
    assert "Changed behavior." in review["evidence"][0]["text"]
    assert "Demo claim." in review["doc_context"][0]["text"]
    assert any("docsync attest claim.demo" in action for action in review["suggested_actions"])

    prompt = review_prompt_for_result(result)
    assert "Claim `claim.demo`: Demo claim." in prompt
    assert "docsync attest claim.demo --evidence evidence.demo" in prompt


def test_sarif_payload_contains_finding_location(tmp_path: Path) -> None:
    """SARIF output exposes DocSync finding locations."""
    _write_repo(tmp_path)
    _commit_all(tmp_path)
    _replace(tmp_path / "src.py", "Demo behavior.", "Changed behavior.")
    result = check_repo(CheckOptions(repo_root=tmp_path, base_ref="HEAD"))

    payload = sarif_payload(result)

    sarif_result = payload["runs"][0]["results"][0]
    assert sarif_result["ruleId"] == "DS201"
    assert (
        sarif_result["locations"][0]["physicalLocation"]["region"]["startLine"]
        == CHANGED_EVIDENCE_LINE
    )


def test_attestation_loader_reports_invalid_and_semantic_findings(tmp_path: Path) -> None:
    """Attestation loader reports malformed and semantically stale records."""
    _write_repo(tmp_path)
    index = build_index(IndexOptions(repo_root=tmp_path))
    attestations_dir = tmp_path / ".docsync" / "attestations"
    attestations_dir.mkdir()
    (attestations_dir / "bad-list.yml").write_text("attestations: nope\n", encoding="utf-8")
    (attestations_dir / "records.yml").write_text(
        """
attestations:
  - invalid
  - id: dup
    claim: missing.claim
    doc_object: docs.readme.demo
    evidence:
      - evidence.demo
    reason: bad_reason
    evidence_fingerprints:
      evidence.demo: stale
  - id: dup
    claim: claim.demo
    doc_object: docs.readme.demo
    evidence:
      - evidence.demo
    reason: internal_refactor_only
    evidence_fingerprints:
      evidence.demo: stale
  - id: bad-reason
    claim: claim.demo
    doc_object: docs.readme.demo
    evidence:
      - evidence.demo
    reason: bad_reason
    evidence_fingerprints:
      evidence.demo: stale
  - id: missing-evidence
    claim: claim.demo
    doc_object: docs.readme.demo
    evidence:
      - missing.evidence
    reason: internal_refactor_only
    evidence_fingerprints: {}
""".lstrip(),
        encoding="utf-8",
    )

    result = load_attestations(index)
    codes = [finding.code for finding in result.findings]

    assert result.records[0].to_json()["doc_object"] == "docs.readme.demo"
    assert "DS301" in codes
    assert "DS302" in codes
    assert "DS303" in codes
    assert "DS304" in codes
    assert "DS305" in codes


def test_attestation_fingerprints_all_evidence_anchors(tmp_path: Path) -> None:
    """Created attestations fingerprint every linked evidence anchor."""
    _write_repo(tmp_path)
    _add_second_evidence_anchor(tmp_path)
    _commit_all(tmp_path)

    path = create_attestation(
        tmp_path,
        "claim.demo",
        ("evidence.demo",),
        "internal_refactor_only",
    )
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    record = payload["attestations"][0]
    anchor_hashes = record["evidence_anchor_fingerprints"]["evidence.demo"]

    assert len(anchor_hashes) == MULTI_ANCHOR_COUNT
    assert record["reviewer"] == "agent"
    assert record["base"] == "HEAD"
    assert record["head"]
    assert record["expires_at"] is None
    assert record["evidence_fingerprints"]["evidence.demo"] == sha256_text("\n".join(anchor_hashes))

    _replace(tmp_path / "src_extra.py", "Second behavior.", "Changed second behavior.")
    result = check_repo(CheckOptions(repo_root=tmp_path, base_ref="HEAD"))
    assert [finding.code for finding in result.findings] == ["DS301", "DS201"]


def test_attestation_loader_reports_audit_findings(tmp_path: Path) -> None:
    """Attestation validation catches missing audit fields and partial anchors."""
    _write_repo(tmp_path)
    _add_second_evidence_anchor(tmp_path)
    index = build_index(IndexOptions(repo_root=tmp_path))
    anchors = tuple(anchor.content_hash for anchor in index.evidence_anchors["evidence.demo"])
    aggregate = sha256_text("\n".join(anchors))
    attestations_dir = tmp_path / ".docsync" / "attestations"
    attestations_dir.mkdir()
    (attestations_dir / "audit.yml").write_text(
        f"""
attestations:
  - id: missing-reviewer
    claim: claim.demo
    doc_object: docs.readme.demo
    evidence:
      - evidence.demo
    reason: internal_refactor_only
    evidence_fingerprints:
      evidence.demo: {aggregate}
    evidence_anchor_fingerprints:
      evidence.demo:
        - {anchors[0]}
        - {anchors[1]}
  - id: expired
    claim: claim.demo
    doc_object: docs.readme.demo
    evidence:
      - evidence.demo
    reason: internal_refactor_only
    reviewer: agent
    expires_at: 2000-01-01T00:00:00Z
    evidence_fingerprints:
      evidence.demo: {aggregate}
    evidence_anchor_fingerprints:
      evidence.demo:
        - {anchors[0]}
        - {anchors[1]}
  - id: partial
    claim: claim.demo
    doc_object: docs.readme.demo
    evidence:
      - evidence.demo
    reason: internal_refactor_only
    reviewer: agent
    evidence_fingerprints:
      evidence.demo: {aggregate}
""".lstrip(),
        encoding="utf-8",
    )

    result = load_attestations(index)
    codes = [finding.code for finding in result.findings]

    assert "DS306" in codes
    assert "DS307" in codes
    assert "DS308" in codes


def test_check_reports_git_diff_errors(tmp_path: Path) -> None:
    """Check reports Git diff errors without crashing."""
    _write_repo(tmp_path)

    result = check_repo(CheckOptions(repo_root=tmp_path, base_ref="HEAD"))

    assert [finding.code for finding in result.findings] == ["DS000"]
    assert "Unable to read Git diff" in result.findings[0].message


def _write_repo(tmp_path: Path) -> None:
    (tmp_path / ".docsync").mkdir()
    (tmp_path / ".docsync" / "config.yml").write_text(
        DEFAULT_CONFIG_TEXT,
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text(
        """
<!-- docsync:object docs.readme.demo -->
# Demo

<!-- docsync:claim claim.demo -->
Demo claim.
<!-- docsync:claim.end claim.demo -->
<!-- docsync:object.end docs.readme.demo -->
""".lstrip(),
        encoding="utf-8",
    )
    (tmp_path / "src.py").write_text(
        """
<!-- docsync:evidence.start evidence.demo -->
Demo behavior.
<!-- docsync:evidence.end evidence.demo -->
""".lstrip(),
        encoding="utf-8",
    )
    (tmp_path / ".docsync" / "trace.yml").write_text(
        """
version: 1
documents:
  docs.readme:
    path: README.md
objects:
  docs.readme.demo:
    document: docs.readme
    kind: heading_section
    path: README.md
    marker: docs.readme.demo
    heading:
      level: 1
      text: Demo
claims:
  claim.demo:
    object: docs.readme.demo
    marker: claim.demo
    text: Demo claim.
    severity: high
    evidence:
      - evidence.demo
    review:
      acceptable_attestation_reasons:
        - internal_refactor_only
evidence:
  evidence.demo:
    type: code
    anchors:
      - path: src.py
        mode: explicit_region
""".lstrip(),
        encoding="utf-8",
    )


def _add_second_evidence_anchor(tmp_path: Path) -> None:
    (tmp_path / "src_extra.py").write_text(
        """
<!-- docsync:evidence.start evidence.demo -->
Second behavior.
<!-- docsync:evidence.end evidence.demo -->
""".lstrip(),
        encoding="utf-8",
    )
    _replace(
        tmp_path / ".docsync" / "trace.yml",
        "      mode: explicit_region\n",
        """      mode: explicit_region
      - path: src_extra.py
        mode: explicit_region
""",
    )


def _commit_all(repo_root: Path) -> None:
    _git(repo_root, "init")
    _git(repo_root, "add", ".")
    _git(
        repo_root,
        "-c",
        "user.name=DocSync Test",
        "-c",
        "user.email=docsync@example.invalid",
        "commit",
        "-m",
        "base",
    )


def _replace(path: Path, old: str, new: str) -> None:
    path.write_text(path.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(
        ("git", *args),
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
