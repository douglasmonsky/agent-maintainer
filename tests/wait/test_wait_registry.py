"""Tests durable wait registry records."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from agent_maintainer.wait.github_pr import (
    GitHubPrCheck,
    GitHubPrChecksState,
    GitHubPrWaitResult,
)
from agent_maintainer.wait.registry import (
    WAIT_STATUS_PENDING,
    WAIT_STATUS_READY,
    WAIT_STATUS_RESUMED,
    RegisterGitHubPrWait,
    WaitRegistry,
    render_resume_text,
    render_wait_record_text,
)


def test_register_github_pr_wait_writes_record(tmp_path: Path) -> None:
    """GitHub PR wait registration persists compact metadata only."""

    registry = WaitRegistry(tmp_path)

    record = registry.register_github_pr(
        RegisterGitHubPrWait(
            root=tmp_path,
            pr_number="291",
            repo="douglasmonsky/agent-maintainer",
            platform="codex",
            branch="codex/background-wait",
            head_sha="abc123",
            interval_seconds=20,
            timeout_seconds=1800,
            now=datetime(2026, 7, 6, 22, 0, tzinfo=UTC),
        ),
    )

    record_path = tmp_path / ".verify-logs" / "waits" / f"{record.wait_id}.json"
    raw_record = record_path.read_text(encoding="utf-8")
    payload = json.loads(raw_record)

    assert record.wait_id == "github-pr-291-20260706T220000Z"
    assert record.status == WAIT_STATUS_PENDING
    assert payload["repo"] == "douglasmonsky/agent-maintainer"
    assert payload["branch"] == "codex/background-wait"
    assert payload["head_sha"] == "abc123"
    assert payload["deadline_at"] == "2026-07-06T22:30:00Z"
    assert registry.read(record.wait_id) == record
    assert not record_path.with_suffix(".json.tmp").exists()
    assert "hook_input" not in raw_record
    assert "token" not in raw_record.lower()


def test_complete_github_pr_wait_prepares_resume(tmp_path: Path) -> None:
    """Terminal PR wait state stores compact resume context."""

    registry = WaitRegistry(tmp_path)
    record = registry.register_github_pr(
        RegisterGitHubPrWait(
            root=tmp_path,
            pr_number="291",
            now=datetime(2026, 7, 6, 22, 0, tzinfo=UTC),
        ),
    )
    result = GitHubPrWaitResult(
        pr_number="291",
        state=GitHubPrChecksState(
            pr_number="291",
            checks=(
                GitHubPrCheck(
                    name="verify",
                    state="failure",
                    conclusion="failure",
                    bucket="fail",
                ),
            ),
        ),
    )

    completed = registry.complete_github_pr(
        record,
        result,
        now=datetime(2026, 7, 6, 22, 5, tzinfo=UTC),
    )

    assert completed.status == WAIT_STATUS_READY
    assert completed.terminal_result == "FAIL"
    assert completed.last_observed_state is not None
    assert completed.last_observed_state["completed"] is True
    assert "Result: FAIL" in completed.resume_message
    assert "GitHub check: verify (failure)" in render_resume_text(completed)
    assert "PR checks reached FAIL for PR #291" in render_resume_text(completed)
    assert registry.read(record.wait_id) == completed


def test_pending_and_resumed_render_compact_text(tmp_path: Path) -> None:
    """Pending and consumed wait records have compact resume text."""

    registry = WaitRegistry(tmp_path)
    record = registry.register_github_pr(
        RegisterGitHubPrWait(root=tmp_path, pr_number="291"),
    )
    resumed = registry.mark_resumed(record)

    assert "Result: PENDING" in render_wait_record_text(record)
    assert "wait resume" in render_wait_record_text(record)
    assert resumed.status == WAIT_STATUS_RESUMED
