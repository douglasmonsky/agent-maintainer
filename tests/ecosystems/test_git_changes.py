"""Tests neutral git change readers for provider-aware reports."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from agent_maintainer.ecosystems import git_changes

GIT_FATAL_EXIT = 128


def test_name_status_z_preserves_change_identity() -> None:
    output = (
        b"A\0new.py\0"
        b"M\0src/a.py\0"
        b"R100\0old.py\0new-name.py\0"
        b"C090\0base.py\0copy.py\0"
        b"T\0typed.bin\0"
        b"U\0conflicted.py\0"
        b"D\0gone.py\0"
    )

    assert git_changes.parse_name_status_z(output) == (
        git_changes.GitPathChange("new.py", "added"),
        git_changes.GitPathChange("src/a.py", "modified"),
        git_changes.GitPathChange("new-name.py", "renamed", old_path="old.py"),
        git_changes.GitPathChange("copy.py", "copied", old_path="base.py"),
        git_changes.GitPathChange("typed.bin", "type-changed"),
        git_changes.GitPathChange("conflicted.py", "unmerged"),
        git_changes.GitPathChange("gone.py", "deleted"),
    )


def test_rename_and_delete_distinguish_affected_from_evidence_paths() -> None:
    renamed = git_changes.GitPathChange(
        "security/new.toml",
        "renamed",
        old_path="security/old.toml",
    )
    deleted = git_changes.GitPathChange("security/gone.toml", "deleted")

    assert renamed.affected_paths() == (
        "security/old.toml",
        "security/new.toml",
    )
    assert renamed.evidence_paths() == ("security/new.toml",)
    assert deleted.affected_paths() == ("security/gone.toml",)
    assert deleted.evidence_paths() == ()


@pytest.mark.parametrize(
    "output",
    (
        b"M\0missing-trailing-nul",
        b"R100\0only-old\0",
        b"Z\0unknown.txt\0",
        b"M\0../escape.txt\0",
        b"M\0bad\xff.txt\0",
    ),
)
def test_name_status_z_rejects_malformed_or_unsafe_output(output: bytes) -> None:
    with pytest.raises(ValueError):
        git_changes.parse_name_status_z(output)


def test_name_status_commands_use_resolved_ref_and_path_terminator() -> None:
    command = git_changes.git_name_status_command("a" * 40, staged=False)
    staged = git_changes.git_name_status_command("", staged=True)

    assert command[-2:] == [f"{'a' * 40}...HEAD", "--"]
    assert "--name-status" in command
    assert "-z" in command
    assert staged[-2:] == ["--cached", "--"]


def test_name_status_resolves_option_shaped_ref_before_diff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(
        git_changes.subprocess,
        "run",
        _sequenced_git_run(calls),
    )

    changes = git_changes.run_git_name_status("--stat", staged=False)

    assert changes == (git_changes.GitPathChange("src/app.py", "modified"),)
    assert calls[0][-2:] == ["--end-of-options", "--stat^{commit}"]
    assert calls[1][-2:] == [f"{'a' * 40}...HEAD", "--"]


def test_name_status_runs_all_git_commands_in_requested_repository(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seen_cwds: list[Path | None] = []

    def fake_run(
        command: list[str],
        *,
        text: bool,
        capture_output: bool,
        check: bool,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]:
        del capture_output, check
        seen_cwds.append(cwd)
        if text:
            return subprocess.CompletedProcess(command, 0, stdout=f"{'a' * 40}\n")
        return subprocess.CompletedProcess(command, 0, stdout=b"M\0src/app.py\0")

    monkeypatch.setattr(git_changes.subprocess, "run", fake_run)

    git_changes.run_git_name_status("main", staged=False, cwd=tmp_path)

    assert seen_cwds == [tmp_path, tmp_path]


def _sequenced_git_run(
    calls: list[list[str]],
) -> Callable[..., subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]]:
    def fake_run(
        command: list[str],
        *,
        text: bool = False,
        capture_output: bool,
        check: bool,
    ) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]:
        calls.append(command)
        assert capture_output
        assert check
        if len(calls) == 1:
            assert text
            return subprocess.CompletedProcess(command, 0, stdout=f"{'a' * 40}\n")
        assert not text
        return subprocess.CompletedProcess(command, 0, stdout=b"M\0src/app.py\0")

    return fake_run


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
