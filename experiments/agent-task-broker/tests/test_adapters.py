"""Tests task broker adapter contracts."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from agent_task_broker.adapters import (
    CodexSdkWorkerBackend,
    DisabledBackend,
    GitWorktreeWorkspaceBackend,
    LocalJsonlTraceSink,
    LocalStateMachineWorkflowEngine,
    ManualWorkerBackend,
    TraceEvent,
    WorkerRun,
    WorkerTask,
    WorkflowTransition,
    WorkspaceHandle,
    disabled_backend_diagnostic,
)
from agent_task_broker.results import ResultInput
from agent_task_broker.store import BrokerStore, TaskInput


def test_manual_worker_returns_domain_result_without_spawning(tmp_path: Path) -> None:
    """Manual worker returns broker domain objects only."""

    task = WorkerTask(
        task_id="task-0001",
        capsule={"task_id": "task-0001", "goal": "Review task"},
    )
    workspace = WorkspaceHandle(
        task_id="task-0001",
        path=tmp_path,
        branch="task/task-0001",
        base="HEAD",
    )

    run = ManualWorkerBackend().run(task, workspace)

    assert isinstance(run, WorkerRun)
    assert run.__class__.__module__ == "agent_task_broker.adapters"
    assert run.status == "manual"
    assert run.result is None
    assert "no agent was spawned" in run.summary


def test_manual_worker_wraps_supplied_result_input(tmp_path: Path) -> None:
    """Manual worker handles local structured results."""

    task = WorkerTask(
        task_id="task-0001",
        capsule={"task_id": "task-0001", "goal": "Review task"},
    )
    workspace = WorkspaceHandle(
        task_id="task-0001",
        path=tmp_path,
        branch="task/task-0001",
        base="HEAD",
    )
    result = ResultInput(
        root=tmp_path,
        task_id="task-0001",
        status="done",
        summary="Done",
        verification=("pytest -q",),
    )

    run = ManualWorkerBackend().run(task, workspace, result)

    assert run.status == "done"
    assert run.summary == "Done"
    assert run.result == {
        "task_id": "task-0001",
        "status": "done",
        "summary": "Done",
        "verification": ["pytest -q"],
        "needs": [],
        "reason": "",
        "changed_files": [],
    }


def test_codex_sdk_backend_plans_request(tmp_path: Path) -> None:
    """Codex SDK worker returns an execution plan without spawning."""

    task = WorkerTask(
        task_id="task-0001",
        capsule={
            "task_id": "task-0001",
            "goal": "Review task",
            "allowed_paths": ["src/pkg.py"],
        },
    )
    workspace = WorkspaceHandle(
        task_id="task-0001",
        path=tmp_path,
        branch="task/task-0001",
        base="HEAD",
    )

    run = CodexSdkWorkerBackend().run(task, workspace)

    assert isinstance(run, WorkerRun)
    assert run.__class__.__module__ == "agent_task_broker.adapters"
    assert run.status == "manual"
    assert "no agent was spawned" in run.summary
    assert run.result is not None
    assert run.result["backend"] == "codex-sdk-plan"
    assert run.result["spawn_enabled"] is False
    assert run.result["orchestrator"] == "codex-sdk"
    assert run.result["sdk"] == {
        "language": "python",
        "package": "openai-codex",
        "client": "AsyncCodex",
        "sandbox": "workspace_write",
    }
    assert run.result["workspace"] == {
        "path": str(tmp_path),
        "branch": "task/task-0001",
        "base": "HEAD",
        "created": False,
    }
    assert "command" not in run.result
    assert run.result["request"]["thread"] == "start"
    assert run.result["request"]["resume_thread_id"] is None
    assert "task-0001" in str(run.result["request"]["prompt"])
    assert "src/pkg.py" in str(run.result["request"]["prompt"])


def test_codex_sdk_backend_wraps_result(tmp_path: Path) -> None:
    """Codex SDK worker wraps supplied local structured results."""

    task = WorkerTask(
        task_id="task-0001",
        capsule={"task_id": "task-0001", "goal": "Review task"},
    )
    workspace = WorkspaceHandle(
        task_id="task-0001",
        path=tmp_path,
        branch="task/task-0001",
        base="HEAD",
    )
    result = ResultInput(
        root=tmp_path,
        task_id="task-0001",
        status="done",
        summary="Done",
        verification=("pytest -q",),
    )

    run = CodexSdkWorkerBackend().run(task, workspace, result)

    assert run.status == "done"
    assert run.summary == "Done"
    assert run.result is not None
    assert "backend" not in run.result
    assert run.result["verification"] == ["pytest -q"]


def test_git_worktree_backend_plan_is_explicit_opt_in(tmp_path: Path) -> None:
    """Planning a worktree does not create one."""

    repo = tmp_path / "repo"
    repo.mkdir()
    backend = GitWorktreeWorkspaceBackend()

    handle = backend.plan(repo, "task-0001")

    assert isinstance(handle, WorkspaceHandle)
    assert handle.__class__.__module__ == "agent_task_broker.adapters"
    assert handle.path == tmp_path / "repo-task-0001"
    assert not handle.path.exists()
    assert handle.created is False
    assert handle.command[:4] == ("git", "-C", str(repo), "worktree")


def test_local_workflow_engine_returns_transitions(tmp_path: Path) -> None:
    """Local workflow engine wraps store state changes in domain transitions."""

    store = BrokerStore(root=tmp_path)
    store.init()
    task = store.add_task(TaskInput(title="Review task"))
    engine = LocalStateMachineWorkflowEngine()

    selected = engine.next_transition(store)
    claimed = engine.claim(store, str(task["id"]), agent="codex")
    finished = engine.finish(
        store,
        ResultInput(
            root=tmp_path,
            task_id=str(task["id"]),
            status="done",
            summary="Done",
            verification=("pytest -q",),
        ),
    )

    assert isinstance(selected, WorkflowTransition)
    assert selected.action == "select"
    assert claimed.from_status == "open"
    assert claimed.to_status == "claimed"
    assert claimed.payload == {"attempt_id": "task-0001-1", "agent": "codex"}
    assert finished.from_status == "claimed"
    assert finished.to_status == "done"
    assert finished.payload["status"] == "done"


def test_trace_sink_writes_local_jsonl_events(tmp_path: Path) -> None:
    """Trace sink writes bounded local JSONL events."""

    sink = LocalJsonlTraceSink(root=tmp_path)

    sink.emit(
        TraceEvent(
            event_name="task.claimed",
            task_id="task-0001",
            status="pass",
            attributes={"backend": "local-state-machine"},
            timestamp=datetime(2026, 7, 6, 19, 20, tzinfo=UTC),
        )
    )

    events_path = tmp_path / ".agent-task-broker" / "traces" / "events.jsonl"
    event = json.loads(events_path.read_text(encoding="utf-8"))

    assert event == {
        "schema_version": 1,
        "event_name": "task.claimed",
        "timestamp": "2026-07-06T19:20:00Z",
        "severity": "info",
        "sensitive": False,
        "command": "task-broker",
        "status": "pass",
        "attributes": {
            "backend": "local-state-machine",
            "task_id": "task-0001",
        },
    }


def test_disabled_backend_diagnostics_are_explicit() -> None:
    """Future optional backends fail closed with diagnostics."""

    diagnostic = disabled_backend_diagnostic(
        "openai-agents-worker",
        "openai-agents",
        install_hint="Install the future worker extra before enabling.",
    )
    disabled = DisabledBackend(
        backend_name="langgraph-workflow",
        dependency="langgraph",
    )

    assert diagnostic.status == "disabled"
    assert diagnostic.reason == "missing optional dependency: openai-agents"
    assert diagnostic.install_hint == "Install the future worker extra before enabling."
    assert disabled.diagnostic().reason == "missing optional dependency: langgraph"
