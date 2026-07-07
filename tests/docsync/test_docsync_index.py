"""Tests for resolved DocSync indexes."""

from __future__ import annotations

from pathlib import Path

from docsync.api import IndexOptions, build_index
from docsync.config.defaults import DEFAULT_CONFIG_TEXT

HEADING_LINE = 2
EVIDENCE_START_LINE = 4
EVIDENCE_END_LINE = 6
EVIDENCE_CONTENT_LINE = 5


def test_index_resolves_doc_objects_and_evidence_spans(tmp_path: Path) -> None:
    """Index contains exact Markdown object and evidence line spans."""
    _write_repo(tmp_path)

    result = build_index(IndexOptions(repo_root=tmp_path))

    assert result.findings == ()
    doc_object = result.doc_objects["docs.readme.demo"]
    assert doc_object.span.start_line == 1
    assert doc_object.heading_line == HEADING_LINE
    assert doc_object.title == "Demo"
    anchor = result.evidence_anchors["evidence.demo"][0]
    assert anchor.span.start_line == EVIDENCE_START_LINE
    assert anchor.span.end_line == EVIDENCE_END_LINE
    assert anchor.content_span.start_line == EVIDENCE_CONTENT_LINE
    assert anchor.content_hash.startswith("sha256:")
    assert result.to_json()["documents"]["docs.readme"] == {
        "document_id": "docs.readme",
        "path": "README.md",
        "title": "Demo Guide",
        "audience": "maintainers",
    }


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

<!-- docsync:evidence.start evidence.demo -->
Demo behavior.
<!-- docsync:evidence.end evidence.demo -->
<!-- docsync:object.end docs.readme.demo -->
""".lstrip(),
        encoding="utf-8",
    )
    (tmp_path / ".docsync" / "trace.yml").write_text(
        """
version: 1
documents:
  docs.readme:
    path: README.md
    title: Demo Guide
    audience: maintainers
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
    severity: medium
    evidence:
      - evidence.demo
evidence:
  evidence.demo:
    type: code
    anchors:
      - path: README.md
        mode: explicit_region
""".lstrip(),
        encoding="utf-8",
    )
