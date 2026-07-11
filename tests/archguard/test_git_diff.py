"""Tests for Archguard git diff path discovery."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from archguard import git_diff


def _command_path(name: str) -> str:
    return f"/bin/{name}"


def test_git_name_only_command_uses_base_ref(monkeypatch: pytest.MonkeyPatch) -> None:
    """Build a base-ref git diff command."""
    monkeypatch.setattr(git_diff.shutil, "which", _command_path)

    assert git_diff.git_name_only_command("origin/main", staged=False) == [
        "/bin/git",
        "diff",
        "--name-only",
        "origin/main",
        "--",
    ]


def test_git_name_only_command_uses_cached_diff(monkeypatch: pytest.MonkeyPatch) -> None:
    """Build a staged git diff command."""
    monkeypatch.setattr(git_diff.shutil, "which", _command_path)

    assert git_diff.git_name_only_command("HEAD", staged=True) == [
        "/bin/git",
        "diff",
        "--name-only",
        "--cached",
        "--",
    ]


def test_changed_paths_normalizes_git_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Normalize changed paths from git output."""

    def fake_run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert command[-1] == "--"
        assert kwargs["cwd"] == tmp_path
        assert kwargs["check"] is True
        return subprocess.CompletedProcess(command, 0, stdout="tach.toml\npkg\\mod.py\n\n")

    monkeypatch.setattr(git_diff.subprocess, "run", fake_run)

    assert git_diff.changed_paths(tmp_path, base_ref="HEAD", staged=False) == (
        "tach.toml",
        "pkg/mod.py",
    )


def test_changed_paths_reports_git_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Convert git diff failures into user-facing runtime errors."""

    def fake_run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise subprocess.CalledProcessError(1, command, stderr="bad ref")

    monkeypatch.setattr(git_diff.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="Could not calculate changed paths"):
        git_diff.changed_paths(tmp_path, base_ref="missing", staged=False)
