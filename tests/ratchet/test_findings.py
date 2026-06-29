"""Tests ratchet finding collection."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from agent_maintainer.ratchet.findings import (
    FILE_LENGTH_CHECK,
    STRUCTURE_CHECK,
    current_findings,
    fingerprint,
)


def test_current_findings_collects_file_length_and_structure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Current findings normalize file-length and structure signals."""

    repo = configured_repo(tmp_path)
    monkeypatch.chdir(repo)

    findings = current_findings()

    checks = {finding.check for finding in findings}
    assert checks == {FILE_LENGTH_CHECK, STRUCTURE_CHECK}
    assert any(finding.metric == "source-lines" for finding in findings)
    assert any(finding.metric == "physical-lines" for finding in findings)
    assert any(finding.metric == "python-files" for finding in findings)
    assert all(finding.fingerprint for finding in findings)


def test_current_findings_can_select_one_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Finding collection honors selected check names."""

    repo = configured_repo(tmp_path)
    monkeypatch.chdir(repo)

    findings = current_findings((STRUCTURE_CHECK,))

    assert {finding.check for finding in findings} == {STRUCTURE_CHECK}


def test_fingerprint_is_stable() -> None:
    """Finding fingerprints are deterministic."""

    assert fingerprint("check", "identity") == fingerprint("check", "identity")
    assert fingerprint("check", "identity") != fingerprint("check", "other")


def configured_repo(tmp_path: Path) -> Path:
    """Create a small repo configured to surface ratchet findings."""

    repo = tmp_path / "repo"
    repo.mkdir()
    write_file(
        repo / "pyproject.toml",
        "\n".join(
            (
                "[tool.agent_maintainer]",
                'mode = "fresh-strict"',
                'file_length_paths = ["src"]',
                'structure_paths = ["src/pkg"]',
                "file_length_max_physical = 2",
                "file_length_max_source = 2",
                "folder_file_warn = 2",
                "folder_file_block = 3",
                "structure_cluster_min = 2",
            ),
        ),
    )
    write_file(repo / "src/pkg/__init__.py", "")
    write_file(repo / "src/pkg/a.py", "a = 1\nb = 2\nc = 3\n")
    write_file(repo / "src/pkg/b.py", "value = 2\n")
    init_git(repo)
    return repo


def write_file(path: Path, text: str) -> None:
    """Write a test file creating parent directories."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def init_git(repo: Path) -> None:
    """Initialize and commit a temporary Git repository."""

    subprocess.run(("git", "init"), cwd=repo, check=True, capture_output=True)
    subprocess.run(("git", "add", "."), cwd=repo, check=True, capture_output=True)
    subprocess.run(
        (
            "git",
            "-c",
            "user.email=test@example.com",
            "-c",
            "user.name=Test User",
            "commit",
            "-m",
            "initial",
        ),
        cwd=repo,
        check=True,
        capture_output=True,
    )
