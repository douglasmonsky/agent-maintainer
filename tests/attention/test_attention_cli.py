"""Tests for attention CLI commands."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from agent_maintainer.attention import cli

ARGUMENT_ERROR_STATUS = 2
MAX_ARGUMENT_ERROR_OUTPUT_CHARS = 300


def test_attention_cli_accepts_repeatable_priority_paths() -> None:
    """Callers can preserve explicitly requested repository paths."""

    args = cli.parse_args(
        [
            "--priority-path",
            "src/app.py",
            "update",
            "--priority-path",
            "tests/test_app.py",
        ]
    )

    assert args.priority_path == ["src/app.py", "tests/test_app.py"]


def test_attention_cli_accepts_equals_priority_path_syntax() -> None:
    """Argparse-supported option syntax is not lost to manual token scanning."""

    args = cli.parse_args(["--priority-path=src/app.py", "update"])

    assert args.priority_path == ["src/app.py"]


def test_attention_cli_reads_priority_paths_from_process_argv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Real module execution preserves options on both sides of the command."""

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "attention",
            "--priority-path",
            "src/app.py",
            "update",
            "--priority-path",
            "tests/test_app.py",
        ],
    )

    args = cli.parse_args(None)

    assert args.priority_path == ["src/app.py", "tests/test_app.py"]


def test_attention_cli_forwards_priority_paths_to_both_build_routes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Update and absent-ledger reads forward the same explicit priorities."""

    _write(tmp_path / "src" / "app.py", "VALUE = 1\n")
    build_spy = Mock(wraps=cli.builder.build_attention_ledger)
    monkeypatch.setattr(cli.builder, "build_attention_ledger", build_spy)
    common = ["--target", str(tmp_path), "--priority-path", "src/app.py"]

    assert cli.main([*common, "top"]) == 0
    capsys.readouterr()
    fallback_call = build_spy.call_args
    assert fallback_call is not None
    assert fallback_call.kwargs["priority_paths"] == ("src/app.py",)

    build_spy.reset_mock()
    assert cli.main([*common, "update"]) == 0
    capsys.readouterr()
    update_call = build_spy.call_args
    assert update_call is not None
    assert update_call.kwargs["priority_paths"] == ("src/app.py",)


def test_attention_cli_renders_invalid_priority_as_argument_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Unsafe explicit paths fail at the CLI boundary without a traceback."""

    unsafe_path = f"../{'x' * 1_000}"
    status = cli.main(["--target", str(tmp_path), "top", "--priority-path", unsafe_path])

    captured = capsys.readouterr()
    assert status == ARGUMENT_ERROR_STATUS
    assert captured.out == ""
    assert "attention argument error: path is not canonical repository-relative" in captured.err
    assert "Traceback" not in captured.err
    assert len(captured.err) <= MAX_ARGUMENT_ERROR_OUTPUT_CHARS


def test_attention_update_top_explain_and_changed(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI writes and reads the attention ledger."""
    _init_repo(tmp_path)
    _write(tmp_path / "src" / "app.py", "VALUE = 1\n")
    _write(tmp_path / "README.md", "# Example\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")
    _write(tmp_path / "src" / "app.py", "VALUE = 2\n")

    assert cli.main(["--target", str(tmp_path), "update"]) == 0
    output = capsys.readouterr().out
    assert "Result: PASS" in output
    assert (tmp_path / ".verify-logs" / "attention" / "files.json").exists()

    assert cli.main(["--target", str(tmp_path), "top", "--limit", "1"]) == 0
    output = capsys.readouterr().out
    assert "Attention Ledger" in output
    assert "src/app.py" in output

    assert cli.main(["--target", str(tmp_path), "top", "--limit", "1", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["returned_file_count"] == 1
    assert len(payload["files"]) == 1

    assert cli.main(["--target", str(tmp_path), "explain", "src/app.py"]) == 0
    output = capsys.readouterr().out
    assert "Attention Explain" in output
    assert "git_changed" in output

    assert cli.main(["--target", str(tmp_path), "changed"]) == 0
    output = capsys.readouterr().out
    assert "Attention Changed" in output
    assert "src/app.py" in output


def _init_repo(path: Path) -> None:
    """Initialize a minimal git repository for CLI tests."""
    _git(path, "init")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Test User")


def _git(path: Path, *args: str) -> None:
    """Run git in a test repository."""
    subprocess.run(("git", *args), cwd=path, check=True, capture_output=True, text=True)


def _write(path: Path, content: str) -> None:
    """Write a file, creating parents."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
