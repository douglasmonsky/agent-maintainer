"""Tests for backend-neutral secret scan runner."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import pytest

from ai_guardrails.runners import secret_scan as run_secret_scan

CURRENT_TREE_FINDING_STATUS = 3
GIT_DIFF_FAILURE_STATUS = 2
GITLEAKS_FINDING_STATUS = 5
GITLEAKS_DISPATCH_STATUS = 7


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


def test_gitleaks_staged_command_uses_stdin_scan() -> None:
    command = run_secret_scan.gitleaks_command(
        run_secret_scan.STAGED_MODE,
        "HEAD",
        Path(".verify-logs/gitleaks-staged.json"),
    )

    assert command[:2] == ["gitleaks", "stdin"]
    assert "--report-path" in command


def test_gitleaks_current_tree_run_invokes_subprocess(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(
            command,
            CURRENT_TREE_FINDING_STATUS,
            stdout="scan stdout\n",
            stderr="scan stderr\n",
        )

    report_path = tmp_path / "nested" / "gitleaks.json"
    args = argparse.Namespace(
        mode=run_secret_scan.CURRENT_TREE_MODE,
        base_ref="origin/main",
        report_path=str(report_path),
    )
    monkeypatch.setattr(run_secret_scan.subprocess, "run", fake_run)

    assert run_secret_scan.run_gitleaks(args) == CURRENT_TREE_FINDING_STATUS
    assert report_path.parent.is_dir()
    assert calls == [
        (
            run_secret_scan.gitleaks_command(
                run_secret_scan.CURRENT_TREE_MODE,
                "origin/main",
                report_path,
            ),
            {"text": True, "capture_output": True, "check": False},
        )
    ]
    output = capsys.readouterr().out
    assert "scan stdout" in output
    assert "scan stderr" in output


def test_gitleaks_staged_scan_skips_empty_diff(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert command == ["git", "diff", "--cached", "--patch"]
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(run_secret_scan.shutil, "which", lambda name: "git")
    monkeypatch.setattr(run_secret_scan.subprocess, "run", fake_run)

    assert run_secret_scan.run_gitleaks_staged(["gitleaks", "stdin"]) == 0


def test_gitleaks_staged_scan_requires_git(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(run_secret_scan.shutil, "which", lambda _name: None)

    assert run_secret_scan.run_gitleaks_staged(["gitleaks", "stdin"]) == 1
    assert "git executable not found." in capsys.readouterr().out


def test_gitleaks_staged_scan_reports_git_diff_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert command == ["/usr/bin/git", "diff", "--cached", "--patch"]
        return subprocess.CompletedProcess(
            command,
            GIT_DIFF_FAILURE_STATUS,
            stdout="diff stdout\n",
            stderr="diff stderr\n",
        )

    monkeypatch.setattr(run_secret_scan.shutil, "which", lambda _name: "/usr/bin/git")
    monkeypatch.setattr(run_secret_scan.subprocess, "run", fake_run)

    assert run_secret_scan.run_gitleaks_staged(["gitleaks", "stdin"]) == GIT_DIFF_FAILURE_STATUS
    output = capsys.readouterr().out
    assert "diff stdout" in output
    assert "diff stderr" in output


def test_gitleaks_staged_scan_passes_diff_to_stdin(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []
    staged_diff = "diff --git a/example.py b/example.py\n"

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((command, kwargs))
        if command == ["/usr/bin/git", "diff", "--cached", "--patch"]:
            return subprocess.CompletedProcess(command, 0, stdout=staged_diff, stderr="")
        return subprocess.CompletedProcess(
            command,
            GITLEAKS_FINDING_STATUS,
            stdout="leak stdout\n",
            stderr="",
        )

    monkeypatch.setattr(run_secret_scan.shutil, "which", lambda _name: "/usr/bin/git")
    monkeypatch.setattr(run_secret_scan.subprocess, "run", fake_run)

    assert run_secret_scan.run_gitleaks_staged(["gitleaks", "stdin"]) == GITLEAKS_FINDING_STATUS
    assert calls[1] == (
        ["gitleaks", "stdin"],
        {
            "input": staged_diff,
            "text": True,
            "capture_output": True,
            "check": False,
        },
    )
    assert "leak stdout" in capsys.readouterr().out


def test_main_dispatches_supported_gitleaks_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_gitleaks(args: argparse.Namespace) -> int:
        assert args.backend == "gitleaks"
        assert args.mode == run_secret_scan.CURRENT_TREE_MODE
        return GITLEAKS_DISPATCH_STATUS

    monkeypatch.setattr(run_secret_scan, "run_gitleaks", fake_run_gitleaks)

    status = run_secret_scan.main(
        [
            "--backend",
            "gitleaks",
            "--mode",
            "current-tree",
            "--report-path",
            ".verify-logs/secret-scan.json",
        ]
    )

    assert status == GITLEAKS_DISPATCH_STATUS


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
