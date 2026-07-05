"""Tests task broker worktree planning."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from agent_task_broker.cli import main
from agent_task_broker.store import BrokerStore, TaskInput
from agent_task_broker.worktrees import build_worktree_plan, render_worktree_plan

CLI_ERROR = 2


def test_worktree_plan_defaults_outside_repo(tmp_path: Path) -> None:
    """Worktree plans default outside the active repository."""
    repo = tmp_path / "repo"
    repo.mkdir()
    plan = build_worktree_plan(repo, "task-0001")
    assert plan.path == tmp_path / "repo-task-0001"
    assert plan.branch == "task/task-0001"
    assert plan.base == "HEAD"
    assert plan.command_for(repo) == (
        "git",
        "-C",
        str(repo),
        "worktree",
        "add",
        "-b",
        "task/task-0001",
        str(tmp_path / "repo-task-0001"),
        "HEAD",
    )


def test_worktree_plan_renders_json_and_markdown(tmp_path: Path) -> None:
    """Worktree plan renders quiet command capsules."""
    repo = tmp_path / "repo"
    repo.mkdir()
    plan = build_worktree_plan(repo, "task-0001", branch="phase-154")
    payload = json.loads(render_worktree_plan(plan, repo, output_format="json"))
    markdown = render_worktree_plan(plan, repo, output_format="markdown")
    assert payload["task_id"] == "task-0001"
    assert payload["branch"] == "phase-154"
    assert payload["command"][:4] == ["git", "-C", str(repo), "worktree"]
    assert "# Worktree Plan: task-0001" in markdown
    assert "git -C" in markdown


def test_worktree_plan_cli_records_plan(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    """Worktree plan command prints and records one task plan."""
    assert main(["--root", str(tmp_path), "init"]) == 0
    assert main(["--root", str(tmp_path), "add", "Plan worktree"]) == 0
    capsys.readouterr()
    assert main(["--root", str(tmp_path), "worktree", "plan", "task-0001", "--format", "json"]) == 0
    output = capsys.readouterr().out
    payload = json.loads(output)
    recorded = json.loads(
        (tmp_path / ".agent-task-broker" / "worktree-plans" / "task-0001.json").read_text(
            encoding="utf-8",
        ),
    )
    assert payload["branch"] == "task/task-0001"
    assert recorded["task_id"] == "task-0001"


def test_worktree_create_reports_git_failure(tmp_path: Path) -> None:
    """Worktree create reports git failure rather than hiding it."""
    store = BrokerStore(tmp_path)
    store.init()
    store.add_task(TaskInput("Create worktree"))
    assert main(["--root", str(tmp_path), "worktree", "create", "task-0001"]) == CLI_ERROR
