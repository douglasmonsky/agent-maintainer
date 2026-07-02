"""Tests neutral git change readers for provider-aware reports."""

from __future__ import annotations

import subprocess

import pytest

from agent_maintainer.ecosystems import git_changes

GIT_FATAL_EXIT = 128


def test_numstat_keeps_dependency_lockfiles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Provider-aware change reading does not inherit Python lockfile excludes."""
    monkeypatch.setattr(git_changes.subprocess, "run", _fake_numstat_run)

    changes = git_changes.run_git_numstat("origin/main", staged=False)

    assert [(change.path, change.added, change.deleted) for change in changes] == [
        ("package-lock.json", 5, 1),
        ("Cargo.lock", 2, 0),
        ("assets/logo.png", 0, 0),
    ]


def test_neutral_numstat_reports_git_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Git failures include the target diff label."""
    monkeypatch.setattr(git_changes.subprocess, "run", _fake_failed_numstat_run)

    with pytest.raises(RuntimeError, match="fatal diff"):
        git_changes.run_git_numstat("origin/main", staged=False)


def _fake_numstat_run(
    command: list[str],
    *,
    text: bool,
    capture_output: bool,
    check: bool,
) -> subprocess.CompletedProcess[str]:
    """Return mixed ecosystem numstat output."""
    assert command[-2:] == ["origin/main", "--"]
    assert text
    assert capture_output
    assert check
    return subprocess.CompletedProcess(
        command,
        0,
        stdout="5\t1\tpackage-lock.json\n2\t0\tCargo.lock\n-\t-\tassets/logo.png\n",
    )


def _fake_failed_numstat_run(
    command: list[str],
    *,
    text: bool,
    capture_output: bool,
    check: bool,
) -> subprocess.CompletedProcess[str]:
    """Raise a git numstat failure."""
    assert text
    assert capture_output
    assert check
    raise subprocess.CalledProcessError(
        GIT_FATAL_EXIT,
        command,
        stderr="fatal diff",
    )
