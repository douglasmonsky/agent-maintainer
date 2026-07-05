"""JSON storage for the task broker incubator."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

BOARD_DIR = ".agent-task-broker"
BOARD_FILE = "board.json"
TASK_STATUS_OPEN = "open"
TASK_STATUS_CLAIMED = "claimed"
TASK_STATUS_DONE = "done"
TASK_STATUS_GIVEN_UP = "given-up"
ACTIVE_STATUSES = {TASK_STATUS_OPEN, TASK_STATUS_CLAIMED}


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

    def init(self, *, force: bool = False) -> dict[str, object]:
        """Initialize broker state."""
        if self.board_path.exists() and not force:
            raise BrokerError("board already exists; use --force to reinitialize")
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.attempts_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        board = {
            "schema_version": 1,
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "tasks": [],
        }
        write_json(self.board_path, board)
        return board

    def add_task(
        self,
        title: str,
        *,
        body: str = "",
        priority: int = 0,
    ) -> dict[str, object]:
        """Add one task."""
        board = self.require_board()
        task_id = next_task_id(board)
        task = {
            "id": task_id,
            "title": title,
            "body": body,
            "priority": priority,
            "status": TASK_STATUS_OPEN,
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "attempts": [],
            "results": [],
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

    def complete_task(self, task_id: str, *, summary: str) -> dict[str, object]:
        """Complete one task."""
        return self.finish_task(task_id, status=TASK_STATUS_DONE, summary=summary)

    def give_up_task(self, task_id: str, *, reason: str) -> dict[str, object]:
        """Mark one task given up."""
        return self.finish_task(task_id, status=TASK_STATUS_GIVEN_UP, summary=reason)

    def finish_task(self, task_id: str, *, status: str, summary: str) -> dict[str, object]:
        """Write result for one task."""
        task = self.require_task(task_id)
        result = {
            "task_id": task_id,
            "status": status,
            "summary": summary,
            "created_at": utc_now(),
        }
        results = list(task.get("results", []))
        results.append(str(self.result_path(task_id).relative_to(self.board_dir)))
        task["results"] = results
        task["status"] = status
        task["updated_at"] = utc_now()
        write_json(self.result_path(task_id), result)
        write_json(self.task_path(task_id), task)
        return result

    def require_board(self) -> dict[str, object]:
        """Return board metadata or fail clearly."""
        if not self.board_path.exists():
            raise BrokerError("board is not initialized; run `agent-task-broker init`")
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


class BrokerError(RuntimeError):
    """Broker operation failed."""


def read_json(path: Path) -> dict[str, object]:
    """Read JSON object."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise BrokerError(f"expected JSON object: {path}")
    return data


def write_json(path: Path, payload: dict[str, object]) -> None:
    """Write deterministic JSON object."""
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


def task_sort_key(task: dict[str, object]) -> tuple[int, str]:
    """Return stable priority sort key."""
    priority = task.get("priority", 0)
    created_at = str(task.get("created_at", ""))
    return (-priority if isinstance(priority, int) else 0, created_at)


def utc_now() -> str:
    """Return stable UTC timestamp."""
    return datetime.now(UTC).isoformat(timespec="seconds")
