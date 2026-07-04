"""Tests for attention CLI commands."""

from __future__ import annotations

import subprocess
from pathlib import Path

from agent_maintainer.attention import cli


def test_attention_update_top_explain_and_changed(tmp_path: Path, capsys) -> None:
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
