"""Adapter contracts for the task broker incubator."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from agent_task_broker.handoff import handoff_payload
from agent_task_broker.results import RESULT_STATUSES, ResultInput, result_payload
from agent_task_broker.store import BrokerStore
from agent_task_broker.worktrees import build_worktree_plan, create_worktree

WORKER_STATUS_MANUAL = "manual"
WORKER_STATUSES = (*RESULT_STATUSES, WORKER_STATUS_MANUAL)
CODEX_SDK_CLIENT = "AsyncCodex"
CODEX_SDK_PACKAGE = "openai-codex"
CODEX_SDK_PLAN_BACKEND = "codex-sdk-plan"
CODEX_SDK_SANDBOX = "workspace_write"


class BackendError(RuntimeError):
    """Adapter backend operation failed."""


@dataclass(frozen=True)
class BackendDiagnostic:
    """Diagnostic for an unavailable optional backend."""

    backend_name: str
    status: str
    reason: str
    install_hint: str = ""


@dataclass(frozen=True)
class WorkerTask:
    """Task capsule passed to worker backends."""

    task_id: str
    capsule: dict[str, object]

    @classmethod
    def from_task(cls, task: dict[str, object]) -> WorkerTask:
        """Build a worker task from broker task state."""

        return cls(task_id=str(task["id"]), capsule=handoff_payload(task))


@dataclass(frozen=True)
class WorkspaceHandle:
    """Workspace selected for one task run."""

    task_id: str
    path: Path
    branch: str
    base: str
    command: tuple[str, ...] = ()
    created: bool = False


@dataclass(frozen=True)
class WorkerRun:
    """Domain result returned by a worker backend."""

    task_id: str
    status: str
    summary: str
    result: dict[str, object] | None = None
    diagnostics: tuple[BackendDiagnostic, ...] = ()

    def __post_init__(self) -> None:
        """Validate worker status."""

        if self.status not in WORKER_STATUSES:
            raise BackendError(f"unknown worker status: {self.status}")


@dataclass(frozen=True)
class WorkflowTransition:
    """Workflow state transition returned by a workflow backend."""

    task_id: str
    from_status: str
    to_status: str
    action: str
    payload: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class TraceEvent:
    """Trace event emitted by task-broker adapters."""

    event_name: str
    task_id: str
    severity: str = "info"
    status: str | None = None
    attributes: Mapping[str, object] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def as_dict(self) -> dict[str, object]:
        """Return JSON-serializable trace event."""

        record: dict[str, object] = {
            "schema_version": 1,
            "event_name": self.event_name,
            "timestamp": _timestamp_text(self.timestamp),
            "severity": self.severity,
            "sensitive": False,
            "command": "task-broker",
            "attributes": {**dict(self.attributes), "task_id": self.task_id},
        }
        if self.status is not None:
            record["status"] = self.status
        return record


@runtime_checkable
class WorkerBackend(Protocol):
    """Worker backend contract."""

    backend_name: str

    def run(
        self,
        task: WorkerTask,
        workspace: WorkspaceHandle,
        result: ResultInput | None = None,
    ) -> WorkerRun:
        """Run or record one task attempt."""


@runtime_checkable
class WorkspaceBackend(Protocol):
    """Workspace backend contract."""

    backend_name: str

    def plan(
        self,
        root: Path,
        task_id: str,
        *,
        path: Path | None = None,
        branch: str | None = None,
        base: str = "HEAD",
    ) -> WorkspaceHandle:
        """Plan a workspace for one task."""

    def create(self, root: Path, handle: WorkspaceHandle) -> WorkspaceHandle:
        """Create a workspace from an explicit plan."""


@runtime_checkable
class WorkflowEngine(Protocol):
    """Workflow engine contract."""

    backend_name: str

    def next_transition(self, store: BrokerStore) -> WorkflowTransition | None:
        """Return the next selectable transition."""

    def claim(self, store: BrokerStore, task_id: str, *, agent: str) -> WorkflowTransition:
        """Claim one task through the workflow."""

    def finish(self, store: BrokerStore, result: ResultInput) -> WorkflowTransition:
        """Finish one task through the workflow."""


@runtime_checkable
class TraceSink(Protocol):
    """Trace sink contract."""

    backend_name: str

    def emit(self, event: TraceEvent) -> None:
        """Emit one trace event."""


@dataclass(frozen=True)
class ManualWorkerBackend:
    """Local worker backend that never spawns agents automatically."""

    backend_name: str = "local-manual"

    def run(
        self,
        task: WorkerTask,
        workspace: WorkspaceHandle,
        result: ResultInput | None = None,
    ) -> WorkerRun:
        """Return a manual placeholder run or wrap supplied result input."""

        if result is None:
            return WorkerRun(
                task_id=task.task_id,
                status=WORKER_STATUS_MANUAL,
                summary="manual backend recorded task capsule; no agent was spawned",
            )

        payload = result_payload(result)
        return WorkerRun(
            task_id=str(payload["task_id"]),
            status=str(payload["status"]),
            summary=result_summary(payload),
            result=payload,
        )


@dataclass(frozen=True)
class CodexSdkWorkerBackend:
    """Plan-only Codex SDK worker backend that never spawns agents."""

    backend_name: str = CODEX_SDK_PLAN_BACKEND

    def run(
        self,
        task: WorkerTask,
        workspace: WorkspaceHandle,
        result: ResultInput | None = None,
    ) -> WorkerRun:
        """Return a Codex SDK worker request plan without executing it."""

        if result is not None:
            return ManualWorkerBackend(backend_name=self.backend_name).run(
                task,
                workspace,
                result,
            )
        request = codex_sdk_worker_request(task, workspace)
        return WorkerRun(
            task_id=task.task_id,
            status=WORKER_STATUS_MANUAL,
            summary="codex sdk backend planned worker request; no agent was spawned",
            result=request,
        )


@dataclass(frozen=True)
class GitWorktreeWorkspaceBackend:
    """Git worktree workspace backend with explicit creation."""

    backend_name: str = "git-worktree"

    def plan(
        self,
        root: Path,
        task_id: str,
        *,
        path: Path | None = None,
        branch: str | None = None,
        base: str = "HEAD",
    ) -> WorkspaceHandle:
        """Return a worktree handle without creating the worktree."""

        plan = build_worktree_plan(
            root,
            task_id,
            path=path,
            branch=branch,
            base=base,
        )
        return WorkspaceHandle(
            task_id=plan.task_id,
            path=plan.path,
            branch=plan.branch,
            base=plan.base,
            command=plan.command_for(root),
            created=False,
        )

    def create(self, root: Path, handle: WorkspaceHandle) -> WorkspaceHandle:
        """Create an explicitly planned worktree."""

        plan = build_worktree_plan(
            root,
            handle.task_id,
            path=handle.path,
            branch=handle.branch,
            base=handle.base,
        )
        result = create_worktree(plan, root)
        if result.returncode != 0:
            raise BackendError(result.stdout + result.stderr)
        return WorkspaceHandle(
            task_id=handle.task_id,
            path=handle.path,
            branch=handle.branch,
            base=handle.base,
            command=handle.command,
            created=True,
        )


@dataclass(frozen=True)
class LocalStateMachineWorkflowEngine:
    """Local deterministic workflow engine over BrokerStore state."""

    backend_name: str = "local-state-machine"

    def next_transition(self, store: BrokerStore) -> WorkflowTransition | None:
        """Return selection transition for the next open task."""

        task = store.next_task()
        if task is None:
            return None
        status = str(task["status"])
        return WorkflowTransition(
            task_id=str(task["id"]),
            from_status=status,
            to_status=status,
            action="select",
            payload={"title": str(task["title"])},
        )

    def claim(self, store: BrokerStore, task_id: str, *, agent: str) -> WorkflowTransition:
        """Claim one task and return the broker transition."""

        before = store.require_task(task_id)
        attempt = store.claim_task(task_id, agent=agent)
        after = store.require_task(task_id)
        return WorkflowTransition(
            task_id=task_id,
            from_status=str(before["status"]),
            to_status=str(after["status"]),
            action="claim",
            payload={"attempt_id": str(attempt["id"]), "agent": agent},
        )

    def finish(self, store: BrokerStore, result: ResultInput) -> WorkflowTransition:
        """Finish one task and return the broker transition."""

        before = store.require_task(result.task_id)
        payload = result_payload(result)
        written = store.finish_task(result.task_id, payload)
        after = store.require_task(result.task_id)
        return WorkflowTransition(
            task_id=result.task_id,
            from_status=str(before["status"]),
            to_status=str(after["status"]),
            action="finish",
            payload=written,
        )


@dataclass(frozen=True)
class LocalJsonlTraceSink:
    """Local JSONL trace sink for task-broker events."""

    root: Path
    path: Path | None = None
    backend_name: str = "local-jsonl"

    @property
    def events_path(self) -> Path:
        """Return event log path."""

        return self.path or self.root / ".agent-task-broker" / "traces" / "events.jsonl"

    def emit(self, event: TraceEvent) -> None:
        """Append one JSONL trace event."""

        path = self.events_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.as_dict(), sort_keys=True) + "\n")


@dataclass(frozen=True)
class DisabledBackend:
    """Placeholder for optional future backend dependencies."""

    backend_name: str
    dependency: str
    install_hint: str = ""

    def diagnostic(self) -> BackendDiagnostic:
        """Return disabled-backend diagnostic."""

        return disabled_backend_diagnostic(
            self.backend_name,
            self.dependency,
            install_hint=self.install_hint,
        )


def disabled_backend_diagnostic(
    backend_name: str,
    dependency: str,
    *,
    install_hint: str = "",
) -> BackendDiagnostic:
    """Return a standard missing-dependency diagnostic."""

    return BackendDiagnostic(
        backend_name=backend_name,
        status="disabled",
        reason=f"missing optional dependency: {dependency}",
        install_hint=install_hint,
    )


def codex_sdk_worker_request(
    task: WorkerTask,
    workspace: WorkspaceHandle,
) -> dict[str, object]:
    """Return deterministic plan for a future Codex SDK worker run."""

    prompt = codex_sdk_worker_prompt(task, workspace)
    return {
        "task_id": task.task_id,
        "status": WORKER_STATUS_MANUAL,
        "backend": CODEX_SDK_PLAN_BACKEND,
        "spawn_enabled": False,
        "orchestrator": "codex-sdk",
        "sdk": {
            "language": "python",
            "package": CODEX_SDK_PACKAGE,
            "client": CODEX_SDK_CLIENT,
            "sandbox": CODEX_SDK_SANDBOX,
        },
        "workspace": {
            "path": str(workspace.path),
            "branch": workspace.branch,
            "base": workspace.base,
            "created": workspace.created,
        },
        "request": {
            "thread": "start",
            "resume_thread_id": None,
            "prompt": prompt,
        },
        "future_execution": {
            "description": (
                "Enable this backend only after wiring the official Codex SDK "
                "runner to execute the request and persist the returned thread."
            ),
            "requires_user_enablement": True,
        },
    }


def codex_sdk_worker_prompt(task: WorkerTask, workspace: WorkspaceHandle) -> str:
    """Return compact prompt for a planned Codex SDK worker."""

    return "\n".join(
        (
            f"Task broker task: {task.task_id}",
            f"Workspace: {workspace.path}",
            f"Branch: {workspace.branch}",
            "Use the handoff capsule below. Stay within allowed paths. "
            "Record the structured task result when done.",
            json.dumps(task.capsule, sort_keys=True),
        ),
    )


def result_summary(payload: dict[str, object]) -> str:
    """Return compact summary for a result payload."""

    for key in ("summary", "reason"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    needs = payload.get("needs")
    if isinstance(needs, list) and needs:
        return ", ".join(str(need) for need in needs)
    return str(payload["status"])


def _timestamp_text(timestamp: datetime) -> str:
    """Return UTC timestamp matching Agent Maintainer runtime events."""

    aware = timestamp.replace(tzinfo=UTC) if timestamp.tzinfo is None else timestamp
    return aware.astimezone(UTC).isoformat().replace("+00:00", "Z")
