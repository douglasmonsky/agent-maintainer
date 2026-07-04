"""Tests for passive DocSync freshness metadata."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from docsync import freshness
from docsync.config.defaults import DEFAULT_CONFIG_TEXT
from docsync.core.models import EvidenceAnchor, LineSpan
from docsync.indexer import build_docsync_index


def test_freshness_reports_missing_live_markers(tmp_path: Path) -> None:
    """Missing object and evidence markers are advisory freshness metadata."""
    _write_missing_marker_repo(tmp_path)
    index = build_docsync_index(tmp_path)

    report = freshness.build_freshness_report(
        index,
        observed_at="2026-07-04T00:00:00+00:00",
    )

    assert report.ok is False
    assert report.objects[0].status == "missing"
    assert report.evidence[0].status == "missing"
    assert report.evidence[0].path == "README.md"
    assert "Repair: run `python -m docsync check`" in freshness.render_freshness_text(
        report,
        None,
    )


def test_repo_state_handles_available_git(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repo state records cheap Git status when available."""
    monkeypatch.setattr(
        freshness,
        "_git_output",
        lambda _repo_root, *args: "abc123" if args == ("rev-parse", "HEAD") else "",
    )
    clean_state = freshness._repo_state(tmp_path)
    assert clean_state.head == "abc123"
    assert clean_state.dirty is False
    assert clean_state.worktree_fingerprint is not None


def test_git_output_handles_os_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Git output returns None when subprocess execution fails."""
    monkeypatch.setattr(freshness.subprocess, "run", raise_os_error)
    assert freshness._git_output(tmp_path, "status") is None


def test_evidence_hash_and_path_fallbacks() -> None:
    """Evidence helpers handle multi-anchor and no-anchor cases."""
    anchors = (
        EvidenceAnchor(
            evidence_id="evidence.demo",
            path=Path("a.py"),
            span=LineSpan(Path("a.py"), 1, 3),
            content_span=LineSpan(Path("a.py"), 2, 2),
            content_hash="sha256:a",
        ),
        EvidenceAnchor(
            evidence_id="evidence.demo",
            path=Path("b.py"),
            span=LineSpan(Path("b.py"), 1, 3),
            content_span=LineSpan(Path("b.py"), 2, 2),
            content_hash="sha256:b",
        ),
    )
    content_hash = freshness._evidence_content_hash(anchors)
    assert content_hash is not None
    assert content_hash.startswith("sha256:")
    assert freshness._evidence_path(object(), ()) is None


def _write_missing_marker_repo(tmp_path: Path) -> None:
    (tmp_path / ".docsync").mkdir()
    (tmp_path / ".docsync" / "config.yml").write_text(
        DEFAULT_CONFIG_TEXT,
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("# Demo\n\nNo markers.\n", encoding="utf-8")
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
claims: {}
evidence:
  evidence.demo:
    type: code
    anchors:
      - path: README.md
        mode: explicit_region
""".lstrip(),
        encoding="utf-8",
    )


def raise_os_error(
    *_args: object,
    **_kwargs: object,
) -> subprocess.CompletedProcess[str]:
    """Raise OSError for subprocess monkeypatch tests."""
    raise OSError
