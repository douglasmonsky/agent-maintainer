"""Tests for passive DocSync freshness metadata."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from docsync import freshness
from docsync.config.defaults import DEFAULT_CONFIG_TEXT
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
    _write_missing_marker_repo(tmp_path)

    def run_git(
        command: tuple[str, ...],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        stdout = "abc123" if command[1:] == ("rev-parse", "HEAD") else ""
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(freshness.subprocess, "run", run_git)
    clean_state = freshness.build_freshness_report(build_docsync_index(tmp_path)).repo
    assert clean_state.head == "abc123"
    assert clean_state.dirty is False
    assert clean_state.worktree_fingerprint is not None


def test_git_output_handles_os_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Git output returns None when subprocess execution fails."""
    _write_missing_marker_repo(tmp_path)
    monkeypatch.setattr(freshness.subprocess, "run", raise_os_error)
    state = freshness.build_freshness_report(build_docsync_index(tmp_path)).repo
    assert state.head is None
    assert state.dirty is None
    assert state.worktree_fingerprint is None


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
