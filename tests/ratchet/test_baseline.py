"""Tests ratchet baseline creation and CLI behavior."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from agent_maintainer.ratchet import baseline as ratchet_baseline
from agent_maintainer.ratchet import cli as ratchet_cli
from agent_maintainer.ratchet.baseline import create_baseline, read_baseline, write_baseline
from agent_maintainer.ratchet.models import (
    BaselineProvenance,
    RatchetBaseline,
    RatchetFinding,
)


def test_create_baseline_records_findings_and_dirty_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Baseline creation stores current findings and provenance."""

    repo = configured_repo(tmp_path)
    monkeypatch.chdir(repo)
    write_file(repo / "src/pkg/a.py", "a = 1\nb = 2\nc = 3\n")

    baseline = create_baseline(base_ref="HEAD", notes="initial")

    assert baseline.provenance.created_by == "agent-maintainer"
    assert baseline.provenance.dirty_state is True
    assert baseline.provenance.notes == "initial"
    assert {finding.check for finding in baseline.findings} == {
        "file-length",
        "structure-cohesion",
    }


def test_baseline_cli_create_and_status_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI can create a baseline and report status as JSON."""

    repo = configured_repo(tmp_path)
    monkeypatch.chdir(repo)
    baseline_path = repo / ".agent-maintainer/ratchet-baseline.json"

    assert ratchet_cli.main(["baseline", "create", "--baseline", str(baseline_path)]) == 0
    capsys.readouterr()
    assert baseline_path.exists()

    assert ratchet_cli.main(["status", "--baseline", str(baseline_path), "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["counts"]["unchanged"] >= 1


def test_baseline_create_refuses_overwrite_without_force(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Create refuses to replace an existing baseline by default."""

    repo = configured_repo(tmp_path)
    monkeypatch.chdir(repo)
    baseline_path = repo / ".agent-maintainer/ratchet-baseline.json"

    assert ratchet_cli.main(["baseline", "create", "--baseline", str(baseline_path)]) == 0
    assert ratchet_cli.main(["baseline", "create", "--baseline", str(baseline_path)]) == 1


def test_read_baseline_round_trips_cli_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Persisted baseline can be loaded from disk."""

    repo = configured_repo(tmp_path)
    monkeypatch.chdir(repo)
    baseline_path = repo / ".agent-maintainer/ratchet-baseline.json"

    assert ratchet_cli.main(["baseline", "refresh", "--baseline", str(baseline_path)]) == 0

    baseline = read_baseline(baseline_path)
    assert baseline.provenance.version == 1
    assert baseline.findings


def test_default_baseline_path_and_selected_checks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Baseline CLI can use configured default path and selected checks."""

    repo = configured_repo(tmp_path)
    monkeypatch.chdir(repo)

    assert ratchet_cli.main(["baseline", "refresh", "--check", "file-length"]) == 0

    baseline = read_baseline(repo / ".agent-maintainer/ratchet-baseline.json")
    assert baseline.provenance.checks == ("file-length",)


def test_status_text_reports_stale_reasons(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Status text includes stale baseline reasons."""

    repo = configured_repo(tmp_path)
    monkeypatch.chdir(repo)
    baseline_path = repo / ".agent-maintainer/ratchet-baseline.json"
    write_baseline(baseline_path, stale_baseline(), force=True)

    assert ratchet_cli.main(["status", "--baseline", str(baseline_path)]) == 0

    output = capsys.readouterr().out
    assert "status:" in output
    assert "stale:" in output
    assert "baseline was created from a dirty worktree" in output


def test_status_missing_baseline_fails(tmp_path: Path) -> None:
    """Status returns nonzero when baseline file is missing."""

    missing_path = tmp_path / "missing.json"

    assert ratchet_cli.main(["status", "--baseline", str(missing_path)]) == 1


def test_explain_command_prints_supported_checks(capsys: pytest.CaptureFixture[str]) -> None:
    """Explain command describes supported ratchet checks."""

    assert ratchet_cli.main(["explain"]) == 0

    output = capsys.readouterr().out
    assert "Supported checks: file-length, structure-cohesion" in output


def test_git_output_returns_unknown_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Git helper degrades when Git cannot run."""

    def fail_run(*_args: object, **_kwargs: object) -> None:
        raise OSError("git unavailable")

    monkeypatch.setattr(ratchet_baseline.subprocess, "run", fail_run)

    assert ratchet_baseline.git_output("status") == "unknown"


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
    write_file(repo / "src/pkg/a.py", "value = 1\n")
    write_file(repo / "src/pkg/b.py", "value = 2\n")
    init_git(repo)
    return repo


def stale_baseline() -> RatchetBaseline:
    """Return a baseline with stale signals."""

    finding = RatchetFinding(
        check="file-length",
        identity="src/deleted.py:source-lines",
        path="src/deleted.py",
        line=None,
        severity="fail",
        metric="source-lines",
        value=10,
        threshold=2,
        message="deleted file was oversized",
        fingerprint="deleted",
    )
    return RatchetBaseline(
        provenance=BaselineProvenance(
            version=1,
            created_at="2026-06-29T00:00:00+00:00",
            created_by="agent-maintainer",
            base_ref="HEAD",
            repo_commit="abc123",
            dirty_state=True,
            mode="legacy-ratchet",
            checks=("file-length",),
            notes="",
        ),
        findings=(finding,),
    )


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
