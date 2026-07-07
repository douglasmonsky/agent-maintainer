"""Tests wait registration Git identity defaults."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_maintainer.wait import cli

PR_NUMBER = "291"


def test_register_github_pr_cli_writes_git_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Wait register CLI stores local branch and head SHA defaults."""

    monkeypatch.setattr(
        "agent_maintainer.wait.cli_register.complete_git_identity",
        lambda root, *, branch, head_sha: ("codex/wait", "abc123"),
    )

    status = cli.main(
        [
            "register",
            "github-pr",
            PR_NUMBER,
            "--repo",
            "douglasmonsky/agent-maintainer",
            "--root",
            str(tmp_path),
            "--format",
            "json",
        ],
    )
    payload = json.loads(capsys.readouterr().out)

    assert status == 0
    assert payload["branch"] == "codex/wait"
    assert payload["head_sha"] == "abc123"


def test_register_github_pr_cli_new_head_creates_new_wait(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """PR wait registration separates active waits by head SHA."""

    heads = iter(("abc123", "def456"))
    monkeypatch.setattr(
        "agent_maintainer.wait.cli_register.complete_git_identity",
        lambda root, *, branch, head_sha: ("codex/wait", next(heads)),
    )

    first_status = cli.main(_register_pr_args(tmp_path))
    first = json.loads(capsys.readouterr().out)
    second_status = cli.main(_register_pr_args(tmp_path))
    second = json.loads(capsys.readouterr().out)

    assert first_status == 0
    assert second_status == 0
    assert first["wait_id"] != second["wait_id"]
    assert first["head_sha"] == "abc123"
    assert second["head_sha"] == "def456"


def _register_pr_args(root: Path) -> list[str]:
    return [
        "register",
        "github-pr",
        PR_NUMBER,
        "--repo",
        "douglasmonsky/agent-maintainer",
        "--root",
        str(root),
        "--format",
        "json",
    ]
