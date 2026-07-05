"""JSON storage for the task broker incubator."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from agent_task_broker.locks import LockConflict, LockRequest, find_lock_conflicts
from agent_task_broker.locks import lock_payload as make_lock_payload
from agent_task_broker.results import STATUS_ABANDONED, STATUS_DONE, ResultInput
from agent_task_broker.results import result_payload as make_result_payload
from agent_task_broker.worktrees import WorktreePlan

BOARD_DIR = ".agent-task-broker"
BOARD_FILE = "board.json"

TASK_STATUS_OPEN = "open"
TASK_STATUS_CLAIMED = "claimed"
TASK_STATUS_DONE = STATUS_DONE
TASK_STATUS_ABANDONED = STATUS_ABANDONED
ACTIVE_STATUSES = {TASK_STATUS_OPEN, TASK_STATUS_CLAIMED}


@dataclass(frozen=True)
class TaskInput:
    """Task creation input."""

    title: str
    body: str = ""
    priority: int = 0
    allowed_paths: tuple[str, ...] = ()
    do_not_edit_paths: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    acceptance_commands: tuple[str, ...] = ()


@dataclass(frozen=True)
class BrokerStore:
    """Task broker state location."""

    root: Path

    @property
    def board_dir(self) -> Path:
        """Return broker state directory."""
        return self.root / BOARD_DIR

    @property
    def board_path(self) -> Path:
        """Return board metadata path."""
        return self.board_dir / BOARD_FILE

    @property
    def tasks_dir(self) -> Path:
        """Return task directory."""
        return self.board_dir / "tasks"

    @property
    def attempts_dir(self) -> Path:
        """Return attempt directory."""
        return self.board_dir / "attempts"

    @property
    def results_dir(self) -> Path:
        """Return result directory."""
        return self.board_dir / "results"

    @property
    def locks_dir(self) -> Path:
        """Return lock directory."""
        return self.board_dir / "locks"

    @property
    def worktree_plans_dir(self) -> Path:
        """Return worktree plan directory."""
        return self.board_dir / "worktree-plans"

    def init(self, *, force: bool = False) -> dict[str, object]:
        """Initialize broker state."""
        if self.board_path.exists() and not force:
            raise BrokerError("board already exists; use --force to reinitialize")
        for directory in (
            self.tasks_dir,
            self.attempts_dir,
            self.results_dir,
            self.locks_dir,
            self.worktree_plans_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)
        board = {"schema_version": 1, "tasks": [], "created_at": utc_now(), "updated_at": utc_now()}
        write_json(self.board_path, board)
        return board

    def add_task(self, task_input: TaskInput) -> dict[str, object]:
        """Add task to board."""
        board = self.require_board()
        task_id = next_task_id(board)
        task = {
            "id": task_id,
            "title": task_input.title,
            "body": task_input.body,
            "priority": task_input.priority,
            "status": TASK_STATUS_OPEN,
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "attempts": [],
            "results": [],
            "allowed_paths": list(task_input.allowed_paths),
            "do_not_edit_paths": list(task_input.do_not_edit_paths),
            "constraints": list(task_input.constraints),
            "evidence": list(task_input.evidence),
            "acceptance_commands": list(task_input.acceptance_commands),
        }
        task_ids = list(board.get("tasks", []))
        task_ids.append(task_id)
        board["tasks"] = task_ids
        board["updated_at"] = utc_now()
        write_json(self.task_path(task_id), task)
        write_json(self.board_path, board)
        return task

    def tasks(self, *, status: str | None = None) -> list[dict[str, object]]:
        """Return tasks sorted for broker selection."""
        board = self.require_board()
        tasks = [self.require_task(str(task_id)) for task_id in board.get("tasks", [])]
        filtered = [task for task in tasks if status is None or task["status"] == status]
        return sorted(filtered, key=task_sort_key)

    def next_task(self) -> dict[str, object] | None:
        """Return next claimable task."""
        tasks = self.tasks(status=TASK_STATUS_OPEN)
        return tasks[0] if tasks else None

    def claim_task(self, task_id: str, *, agent: str) -> dict[str, object]:
        """Claim one open task."""
        task = self.require_task(task_id)
        if task["status"] not in ACTIVE_STATUSES:
            raise BrokerError(f"task {task_id} is not claimable")
        attempt_id = f"{task_id}-{len(task.get('attempts', [])) + 1}"
        attempt = {
            "id": attempt_id,
            "task_id": task_id,
            "agent": agent,
            "status": "claimed",
            "created_at": utc_now(),
        }
        attempts = list(task.get("attempts", []))
        attempts.append(attempt_id)
        task["attempts"] = attempts
        task["status"] = TASK_STATUS_CLAIMED
        task["claimed_by"] = agent
        task["updated_at"] = utc_now()
        write_json(self.attempt_path(attempt_id), attempt)
        write_json(self.task_path(task_id), task)
        return attempt

    def complete_task(
        self,
        task_id: str,
        *,
        summary: str,
        verification: list[str],
        changed_files: list[str] | None = None,
    ) -> dict[str, object]:
        """Complete one task."""
        result = make_result_payload(
            ResultInput(
                root=self.root,
                task_id=task_id,
                status=TASK_STATUS_DONE,
                summary=summary,
                verification=tuple(verification),
                changed_files=tuple(changed_files or []),
            ),
        )
        return self.finish_task(task_id, result)

    def give_up_task(self, task_id: str, *, reason: str) -> dict[str, object]:
        """Mark one task abandoned."""
        result = make_result_payload(
            ResultInput(
                root=self.root,
                task_id=task_id,
                status=TASK_STATUS_ABANDONED,
                summary=reason,
                reason=reason,
            ),
        )
        return self.finish_task(task_id, result)

    def result_task(self, result: dict[str, object]) -> dict[str, object]:
        """Write an arbitrary validated result."""
        task_id = str(result["task_id"])
        return self.finish_task(task_id, result)

    def finish_task(self, task_id: str, result: dict[str, object]) -> dict[str, object]:
        """Write result for one task."""
        task = self.require_task(task_id)
        result = {**result, "created_at": utc_now()}
        results = list(task.get("results", []))
        results.append(str(self.result_path(task_id).relative_to(self.board_dir)))
        task["results"] = results
        task["status"] = result["status"]
        task["updated_at"] = utc_now()
        write_json(self.result_path(task_id), result)
        write_json(self.task_path(task_id), task)
        return result

    def locks(self) -> list[dict[str, object]]:
        """Return active locks."""
        self.require_board()
        return sorted(
            (read_json(path) for path in self.locks_dir.glob("*.json")),
            key=lambda lock: str(lock.get("id", "")),
        )

    def claim_lock(self, request: LockRequest) -> dict[str, object]:
        """Claim one lock if it does not conflict."""
        self.require_task(request.task_id)
        conflicts = find_lock_conflicts(self.locks(), request)
        if conflicts:
            raise LockConflictError(conflicts)
        lock_id = next_lock_id(self.locks())
        payload = {**make_lock_payload(lock_id, request), "created_at": utc_now()}
        write_json(self.lock_path(lock_id), payload)
        return payload

    def release_lock(self, lock_id: str) -> dict[str, object]:
        """Release one lock."""
        path = self.lock_path(lock_id)
        if not path.exists():
            raise BrokerError(f"lock not found: {lock_id}")
        payload = read_json(path)
        path.unlink()
        return payload

    def record_worktree_plan(self, plan: WorktreePlan) -> dict[str, object]:
        """Write worktree plan for one task."""
        self.require_task(plan.task_id)
        payload = {**plan.payload(self.root), "created_at": utc_now()}
        write_json(self.worktree_plan_path(plan.task_id), payload)
        return payload

    def require_board(self) -> dict[str, object]:
        """Return board metadata or fail clearly."""
        if not self.board_path.exists():
            raise BrokerError("board not initialized; run `agent-task-broker init`")
        return read_json(self.board_path)

    def require_task(self, task_id: str) -> dict[str, object]:
        """Return task or fail clearly."""
        path = self.task_path(task_id)
        if not path.exists():
            raise BrokerError(f"task not found: {task_id}")
        return read_json(path)

    def task_path(self, task_id: str) -> Path:
        """Return task path."""
        return self.tasks_dir / f"{task_id}.json"

    def attempt_path(self, attempt_id: str) -> Path:
        """Return attempt path."""
        return self.attempts_dir / f"{attempt_id}.json"

    def result_path(self, task_id: str) -> Path:
        """Return result path."""
        return self.results_dir / f"{task_id}.json"

    def lock_path(self, lock_id: str) -> Path:
        """Return lock path."""
        return self.locks_dir / f"{lock_id}.json"

    def worktree_plan_path(self, task_id: str) -> Path:
        """Return worktree plan path."""
        return self.worktree_plans_dir / f"{task_id}.json"


class BrokerError(RuntimeError):
    """Broker operation failed."""


class LockConflictError(BrokerError):
    """Lock request conflicted with active locks."""

    def __init__(self, conflicts: list[LockConflict]) -> None:
        """Initialize from lock conflicts."""
        self.conflicts = conflicts
        details = ", ".join(
            f"{conflict.lock_id}({conflict.task_id}:{conflict.mode}:{conflict.target})"
            for conflict in conflicts
        )
        super().__init__(f"lock conflict: {details}")


def read_json(path: Path) -> dict[str, object]:
    """Read JSON object."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise BrokerError(f"expected JSON object: {path}")
    return data


def write_json(path: Path, payload: dict[str, object]) -> None:
    """Write stable JSON object."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def next_task_id(board: dict[str, object]) -> str:
    """Return next stable task id."""
    tasks = board.get("tasks", [])
    if not isinstance(tasks, list):
        raise BrokerError("board tasks must be a list")
    return f"task-{len(tasks) + 1:04d}"


def next_lock_id(locks: list[dict[str, object]]) -> str:
    """Return next stable lock id."""
    return f"lock-{len(locks) + 1:04d}"


def task_sort_key(task: dict[str, object]) -> tuple[int, str]:
    """Return stable priority sort key."""
    priority = task.get("priority", 0)
    created_at = str(task.get("created_at", ""))
    return (-priority if isinstance(priority, int) else 0, created_at)


def utc_now() -> str:
    """Return stable UTC timestamp."""
    return datetime.now(UTC).isoformat(timespec="seconds")
