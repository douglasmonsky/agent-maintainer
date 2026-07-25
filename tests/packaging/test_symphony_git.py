"""Tests for the restricted Symphony Git publication bridge."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[2] / "scripts" / "symphony-git"
SOURCE_REF = "codex/dashboard-history"


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ("git", *args),
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _workspace(tmp_path: Path) -> tuple[Path, Path]:
    remote = tmp_path / "remote.git"
    seed = tmp_path / "seed"
    workspace_root = tmp_path / "workspaces"
    workspace = workspace_root / "GH-6"

    _git(tmp_path, "init", "--bare", str(remote))
    _git(tmp_path, "init", "-b", SOURCE_REF, str(seed))
    _git(seed, "config", "user.name", "Test User")
    _git(seed, "config", "user.email", "test@example.com")
    (seed / "README.md").write_text("# Test\n", encoding="utf-8")
    (seed / "NOTES.md").write_text("# Notes\n", encoding="utf-8")
    _git(seed, "add", "README.md", "NOTES.md")
    _git(seed, "commit", "-m", "initial")
    _git(seed, "remote", "add", "origin", str(remote))
    _git(seed, "push", "-u", "origin", SOURCE_REF)

    workspace_root.mkdir()
    _git(workspace_root, "clone", "--branch", SOURCE_REF, str(remote), str(workspace))
    _git(workspace, "config", "user.name", "Test User")
    _git(workspace, "config", "user.email", "test@example.com")
    _git(workspace, "switch", "-c", "codex/symphony-gh-6")
    return workspace, remote


def _publish(workspace: Path, *paths: str) -> subprocess.CompletedProcess[str]:
    environment = {
        **os.environ,
        "SYMPHONY_WORKSPACE_ROOT": str(workspace.parent),
        "SYMPHONY_SOURCE_REF": SOURCE_REF,
    }
    return subprocess.run(
        (str(SCRIPT), "publish", "docs: test resumed publish", *paths),
        cwd=workspace,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )


def test_publish_resumes_a_clean_authorized_commit(tmp_path: Path) -> None:
    """A circuit-breaker interruption after commit can safely resume at push."""
    workspace, remote = _workspace(tmp_path)
    (workspace / "README.md").write_text("# Test\n\nDocumented.\n", encoding="utf-8")
    _git(workspace, "add", "README.md")
    _git(workspace, "commit", "-m", "docs: document behavior")
    head_before = _git(workspace, "rev-parse", "HEAD")

    result = _publish(workspace, "README.md")

    assert result.returncode == 0, result.stderr
    assert _git(workspace, "rev-parse", "HEAD") == head_before
    assert _git(remote, "rev-parse", "refs/heads/codex/symphony-gh-6") == head_before


def test_publish_commits_and_pushes_an_authorized_worktree_change(tmp_path: Path) -> None:
    """The normal first-attempt publication path remains intact."""
    workspace, remote = _workspace(tmp_path)
    (workspace / "README.md").write_text("# Test\n\nDocumented.\n", encoding="utf-8")

    result = _publish(workspace, "README.md")

    assert result.returncode == 0, result.stderr
    assert _git(workspace, "log", "-1", "--format=%s") == "docs: test resumed publish"
    assert _git(remote, "rev-parse", "refs/heads/codex/symphony-gh-6") == _git(
        workspace,
        "rev-parse",
        "HEAD",
    )


def test_publish_rejects_committed_paths_outside_the_allowlist(tmp_path: Path) -> None:
    """Resume mode remains fail-closed when the commit contains another path."""
    workspace, remote = _workspace(tmp_path)
    (workspace / "README.md").write_text("# Test\n\nDocumented.\n", encoding="utf-8")
    (workspace / "NOTES.md").write_text("# Notes\n\nUnexpected.\n", encoding="utf-8")
    _git(workspace, "add", "README.md", "NOTES.md")
    _git(workspace, "commit", "-m", "docs: mixed change")

    result = _publish(workspace, "README.md")

    assert result.returncode != 0
    assert "exactly match" in result.stderr
    with pytest.raises(subprocess.CalledProcessError):
        _git(remote, "rev-parse", "refs/heads/codex/symphony-gh-6")
