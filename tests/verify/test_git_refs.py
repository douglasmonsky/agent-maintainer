"""Tests verifier Git reference validation."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from agent_maintainer.verify import git_refs


def test_ref_failures_skips_non_git_directories(tmp_path: Path) -> None:
    assert (
        git_refs.ref_failures(
            tmp_path,
            base_ref="HEAD",
            compare_branch="origin/main",
            validate_compare_branch=True,
        )
        == ()
    )


def test_ref_failures_reports_missing_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(git_refs.shutil, "which", lambda _name: None)

    failures = git_refs.ref_failures(
        tmp_path,
        base_ref="HEAD",
        compare_branch="origin/main",
        validate_compare_branch=True,
    )

    assert failures == ("git executable was not found; cannot validate --base-ref.",)


def test_ref_failures_validates_base_ref_only_for_local_profiles(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".git").mkdir()
    checked_refs: list[str] = []

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        checked_refs.append(command[-1])
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(git_refs.shutil, "which", lambda _name: "/usr/bin/git")
    monkeypatch.setattr(git_refs.subprocess, "run", fake_run)

    failures = git_refs.ref_failures(
        tmp_path,
        base_ref="HEAD",
        compare_branch="origin/main",
        validate_compare_branch=False,
    )

    assert failures == ()
    assert checked_refs == ["HEAD^{commit}"]


def test_ref_failures_validates_compare_ref_for_ci_profiles(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".git").mkdir()
    checked_refs: list[str] = []

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        checked_refs.append(command[-1])
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(git_refs.shutil, "which", lambda _name: "/usr/bin/git")
    monkeypatch.setattr(git_refs.subprocess, "run", fake_run)

    failures = git_refs.ref_failures(
        tmp_path,
        base_ref="HEAD",
        compare_branch="origin/main",
        validate_compare_branch=True,
    )

    assert failures == ()
    assert checked_refs == ["HEAD^{commit}", "origin/main^{commit}"]


def test_validate_ref_rejects_whitespace_without_running_git(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        pytest.fail("git should not run for syntactically invalid refs")

    monkeypatch.setattr(git_refs.subprocess, "run", fail_run)

    assert git_refs.validate_ref(tmp_path, "/usr/bin/git", "--base-ref", " HEAD") == (
        "--base-ref must be a non-empty Git ref without surrounding whitespace."
    )
