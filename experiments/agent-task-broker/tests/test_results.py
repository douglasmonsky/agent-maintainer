"""Tests for structured task results."""

from __future__ import annotations

from pathlib import Path

import pytest
from agent_task_broker.results import ResultError, ResultInput, normalize_repo_path, result_payload
from agent_task_broker.store import BrokerStore, TaskInput


def test_done_result_requires_verification(tmp_path: Path) -> None:
    """Done results require verification evidence."""
    with pytest.raises(ResultError, match="done result requires"):
        result_payload(ResultInput(root=tmp_path, task_id="task-0001", status="done"))


def test_blocked_result_requires_needs(tmp_path: Path) -> None:
    """Blocked results require needs."""
    with pytest.raises(ResultError, match="blocked result requires"):
        result_payload(ResultInput(root=tmp_path, task_id="task-0001", status="blocked"))


def test_escalate_and_abandoned_require_reason(tmp_path: Path) -> None:
    """Escalation-like statuses require reason."""
    with pytest.raises(ResultError, match="escalate result requires"):
        result_payload(ResultInput(root=tmp_path, task_id="task-0001", status="escalate"))
    with pytest.raises(ResultError, match="abandoned result requires"):
        result_payload(ResultInput(root=tmp_path, task_id="task-0001", status="abandoned"))


def test_changed_files_normalized_repo_relative(tmp_path: Path) -> None:
    """Changed files are stored repo-relative."""
    source = tmp_path / "src" / "pkg.py"
    source.parent.mkdir()
    source.write_text("", encoding="utf-8")

    assert normalize_repo_path(tmp_path, str(source)) == "src/pkg.py"
    assert normalize_repo_path(tmp_path, "tests/test_pkg.py") == "tests/test_pkg.py"
    with pytest.raises(ResultError, match="escapes repository"):
        normalize_repo_path(tmp_path, "../outside.py")


def test_store_writes_validated_results(tmp_path: Path) -> None:
    """Store writes done and abandoned result files."""
    store = BrokerStore(tmp_path)
    store.init()
    store.add_task(TaskInput("Finish me"))
    done = store.complete_task(
        "task-0001",
        summary="Done",
        verification=["pytest -q"],
        changed_files=["src/pkg.py"],
    )
    assert done["status"] == "done"
    assert done["changed_files"] == ["src/pkg.py"]

    store.add_task(TaskInput("Give up"))
    abandoned = store.give_up_task("task-0002", reason="needs-stronger-model")
    assert abandoned["status"] == "abandoned"
    assert abandoned["reason"] == "needs-stronger-model"
