"""Tests for task handoff capsules."""

from __future__ import annotations

import json
from pathlib import Path

from agent_task_broker.cli import main
from agent_task_broker.handoff import handoff_payload, render_handoff
from agent_task_broker.store import BrokerStore, TaskInput


def test_handoff_payload_includes_repair_contract_fields(tmp_path: Path) -> None:
    """Handoff payload includes compact scope, evidence, and result schema."""
    store = BrokerStore(tmp_path)
    store.init()
    task = store.add_task(
        TaskInput(
            title="Refactor reporting",
            body="Split rendering helper.",
            allowed_paths=("src/reporting.py",),
            do_not_edit_paths=("pyproject.toml",),
            constraints=("Use apply_patch.",),
            evidence=(".verify-logs/runs/run-1/summary.md",),
            acceptance_commands=("pytest tests/test_reporting.py -q",),
        )
    )

    payload = handoff_payload(task)

    assert payload["goal"] == "Refactor reporting"
    assert payload["allowed_paths"] == ["src/reporting.py"]
    assert payload["do_not_edit_paths"] == ["pyproject.toml"]
    assert payload["constraints"] == ["Use apply_patch."]
    assert payload["evidence"] == [".verify-logs/runs/run-1/summary.md"]
    assert payload["acceptance_commands"] == ["pytest tests/test_reporting.py -q"]
    assert "result_schema" in payload


def test_handoff_renders_markdown_and_json(tmp_path: Path) -> None:
    """Handoff renderer supports Markdown and JSON."""
    store = BrokerStore(tmp_path)
    store.init()
    task = store.add_task(TaskInput("Add tests", acceptance_commands=("pytest -q",)))

    markdown = render_handoff(task, output_format="markdown")
    payload = json.loads(render_handoff(task, output_format="json"))

    assert "# Task Handoff: task-0001" in markdown
    assert "## Acceptance commands" in markdown
    assert payload["task_id"] == "task-0001"


def test_handoff_cli_outputs_json(tmp_path: Path, capsys) -> None:
    """CLI handoff command prints JSON capsule."""
    store = BrokerStore(tmp_path)
    store.init()
    store.add_task(TaskInput("CLI handoff"))

    assert main(["--root", str(tmp_path), "handoff", "task-0001", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["goal"] == "CLI handoff"
