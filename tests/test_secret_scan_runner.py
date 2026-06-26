"""Tests for backend-neutral secret scan runner."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts import run_secret_scan


def test_gitleaks_current_tree_command_uses_dir_scan() -> None:
    command = run_secret_scan.gitleaks_command(
        run_secret_scan.CURRENT_TREE_MODE,
        "origin/main",
        Path(".verify-logs/gitleaks.json"),
    )

    assert command[:2] == ["gitleaks", "dir"]
    assert command[-1] == "."
    assert "--redact" in command


def test_gitleaks_range_command_uses_base_ref_log_opts() -> None:
    command = run_secret_scan.gitleaks_command(
        run_secret_scan.RANGE_MODE,
        "origin/main",
        Path(".verify-logs/gitleaks.json"),
    )

    assert command[:2] == ["gitleaks", "git"]
    assert "--log-opts=--all origin/main..HEAD" in command


def test_gitleaks_history_command_uses_all_history_log_opts() -> None:
    command = run_secret_scan.gitleaks_command(
        run_secret_scan.HISTORY_MODE,
        "HEAD",
        Path(".verify-logs/gitleaks-history.json"),
    )

    assert command[:2] == ["gitleaks", "git"]
    assert "--log-opts=--all" in command


def test_gitleaks_staged_scan_skips_empty_diff(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert command == ["git", "diff", "--cached", "--patch"]
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(run_secret_scan.shutil, "which", lambda name: "git")
    monkeypatch.setattr(run_secret_scan.subprocess, "run", fake_run)

    assert run_secret_scan.run_gitleaks_staged(["gitleaks", "stdin"]) == 0


def test_unsupported_secret_scanner_backend_fails(capsys: pytest.CaptureFixture[str]) -> None:
    status = run_secret_scan.main(
        [
            "--backend",
            "betterleaks",
            "--mode",
            "current-tree",
            "--report-path",
            ".verify-logs/secret-scan.json",
        ]
    )

    assert status == 1
    assert "Unsupported secret scanner backend" in capsys.readouterr().out
