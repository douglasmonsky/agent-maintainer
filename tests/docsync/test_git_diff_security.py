"""Security tests for DocSync Git revision handling."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from docsync.git import diff as git_diff
from docsync.git.diff import GitDiffError, changed_line_spans
from docsync.git.process import GitProcessResult


def test_git_diff_rejects_option_like_base_before_outside_write(tmp_path: Path) -> None:
    """A direct API caller cannot convert a base ref into a Git output option."""

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    outside = tmp_path / "outside.diff"
    outside.write_text("unchanged\n", encoding="utf-8")

    with pytest.raises(GitDiffError, match="non-option Git revision"):
        changed_line_spans(repo_root, f"--output={outside}")

    assert outside.read_text(encoding="utf-8") == "unchanged\n"


def test_git_diff_disables_external_diff_and_text_conversion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Diff argv blocks both classes of configured content helper."""

    captured: list[tuple[str, ...]] = []

    def fake_run_git(_repo_root: Path, args: tuple[str, ...]) -> GitProcessResult:
        captured.append(args)
        return GitProcessResult(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(git_diff, "_run_git", fake_run_git)

    assert changed_line_spans(tmp_path, "HEAD") == ()
    assert captured == [
        (
            "diff",
            "--unified=0",
            "--no-ext-diff",
            "--no-textconv",
            "HEAD",
            "--",
        )
    ]


def test_git_diff_rejects_oversized_stdout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Git output is stopped once it crosses the configured byte ceiling."""

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _install_fake_git(
        tmp_path,
        monkeypatch,
        "printf '0123456789012345678901234567890123456789\\n'\n",
    )
    monkeypatch.setattr(git_diff, "MAX_GIT_OUTPUT_BYTES", 16)

    with pytest.raises(GitDiffError, match="stdout exceeds the 16-byte limit"):
        changed_line_spans(repo_root, "HEAD")


def test_git_diff_stops_timed_out_process(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-responsive Git process is killed at the configured deadline."""

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _install_fake_git(tmp_path, monkeypatch, "exec /bin/sleep 2\n")
    monkeypatch.setattr(git_diff, "GIT_TIMEOUT_SECONDS", 0.05)

    with pytest.raises(GitDiffError, match=r"timed out after 0\.05 seconds"):
        changed_line_spans(repo_root, "HEAD")


def _install_fake_git(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    body: str,
) -> None:
    executable_dir = tmp_path / "bin"
    executable_dir.mkdir()
    executable = executable_dir / "git"
    executable.write_text(f"#!/bin/sh\n{body}", encoding="utf-8")
    executable.chmod(0o700)
    current_path = os.environ.get("PATH", "")
    monkeypatch.setenv("PATH", f"{executable_dir}{os.pathsep}{current_path}")
