"""Tests for DocSync changed-claim checks."""

from __future__ import annotations

import subprocess
from pathlib import Path

from docsync.api import CheckOptions, IndexOptions, build_index, check_repo, create_attestation
from docsync.attestations.load import load_attestations
from docsync.config.defaults import DEFAULT_CONFIG_TEXT
from docsync.reports.sarif import sarif_payload

CHANGED_EVIDENCE_LINE = 2


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

Demo claim.
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
