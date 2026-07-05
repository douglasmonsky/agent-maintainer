"""Tests task broker lock rules."""

from __future__ import annotations

from pathlib import Path

import pytest
from agent_task_broker.cli import main
from agent_task_broker.locks import LockRequest, find_lock_conflicts
from agent_task_broker.store import BrokerStore, LockConflictError, TaskInput


def test_read_locks_can_overlap(tmp_path: Path) -> None:
    """Read locks do not conflict with other read locks."""
    store = BrokerStore(tmp_path)
    store.init()
    first = store.add_task(TaskInput("Reader one"))
    second = store.add_task(TaskInput("Reader two"))
    store.claim_lock(
        LockRequest(
            task_id=str(first["id"]),
            kind="path",
            target="src/pkg.py",
            mode="read",
        ),
    )
    lock = store.claim_lock(
        LockRequest(
            task_id=str(second["id"]),
            kind="path",
            target="./src/pkg.py",
            mode="read",
        ),
    )
    assert lock["id"] == "lock-0002"


def test_write_lock_conflicts_with_overlapping_path(tmp_path: Path) -> None:
    """Write locks conflict when exact paths overlap."""
    store = BrokerStore(tmp_path)
    store.init()
    first = store.add_task(TaskInput("Writer one"))
    second = store.add_task(TaskInput("Writer two"))
    store.claim_lock(LockRequest(str(first["id"]), "path", "src/pkg.py", "write"))
    with pytest.raises(LockConflictError, match="lock-0001"):
        store.claim_lock(LockRequest(str(second["id"]), "path", "src/pkg.py", "write"))


def test_glob_lock_conflicts_with_matching_path() -> None:
    """Glob locks conflict with matching paths."""
    conflicts = find_lock_conflicts(
        [
            {
                "id": "lock-0001",
                "task_id": "task-0001",
                "kind": "path",
                "target": "docs/**/*.md",
                "mode": "write",
            },
        ],
        LockRequest("task-0002", "doc", "docs/reference/setup.md", "write"),
    )
    assert conflicts[0].lock_id == "lock-0001"


def test_package_lock_conflicts_with_child_path(tmp_path: Path) -> None:
    """Package locks conflict with child path locks."""
    store = BrokerStore(tmp_path)
    store.init()
    first = store.add_task(TaskInput("Package owner"))
    second = store.add_task(TaskInput("File owner"))
    store.claim_lock(LockRequest(str(first["id"]), "package", "src/pkg", "exclusive"))
    with pytest.raises(LockConflictError, match="task-0001"):
        store.claim_lock(LockRequest(str(second["id"]), "path", "src/pkg/module.py", "write"))


def test_lock_cli_lists_and_releases(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    """Lock CLI can claim, list, and release locks."""
    assert main(["--root", str(tmp_path), "init"]) == 0
    assert main(["--root", str(tmp_path), "add", "Lock task"]) == 0
    assert (
        main(
            [
                "--root",
                str(tmp_path),
                "lock",
                "claim",
                "task-0001",
                "--kind",
                "config",
                "--target",
                "pyproject.toml",
                "--mode",
                "exclusive",
            ],
        )
        == 0
    )
    assert main(["--root", str(tmp_path), "locks"]) == 0
    assert main(["--root", str(tmp_path), "lock", "release", "lock-0001"]) == 0
    assert main(["--root", str(tmp_path), "locks"]) == 0
    output = capsys.readouterr().out
    assert "LOCKED lock-0001 task-0001 exclusive config pyproject.toml" in output
    assert "RELEASED lock-0001 task-0001 pyproject.toml" in output
    assert output.rstrip().endswith("No locks.")
