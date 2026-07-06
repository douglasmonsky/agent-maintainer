"""Tests durable wait registry records."""

from __future__ import annotations

import json
from datetime import datetime
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
    WaitRecord,
    WaitRegistry,
    render_resume_text,
    render_wait_record_text,
)

NOW = datetime.fromisoformat("2026-07-06T22:00:00+00:00")
LATER = datetime.fromisoformat("2026-07-06T22:05:00+00:00")
INTERVAL_SECONDS = 20
TIMEOUT_SECONDS = 1800
EXPECTED_WAIT_ID = "github-pr-291-20260706T220000Z"


def test_register_github_pr_wait_metadata(tmp_path: Path) -> None:
    """GitHub PR wait registration stores core metadata."""

    registry = WaitRegistry(tmp_path)

    record = register_wait(registry, tmp_path)

    assert record.wait_id == EXPECTED_WAIT_ID
    assert record.status == WAIT_STATUS_PENDING
    assert record.repo == "douglasmonsky/agent-maintainer"
    assert record.branch == "codex/background-wait"
    assert record.deadline_at == "2026-07-06T22:30:00Z"


def test_register_github_pr_wait_persists_safely(tmp_path: Path) -> None:
    """GitHub PR wait registration persists compact metadata only."""

    registry = WaitRegistry(tmp_path)

    record = register_wait(registry, tmp_path)
    record_path = wait_record_path(tmp_path, record)
    raw_record = record_path.read_text(encoding="utf-8")
    payload = json.loads(raw_record)

    assert payload["head_sha"] == "abc123"
    assert registry.read(record.wait_id) == record
    assert not record_path.with_suffix(".json.tmp").exists()
    assert "hook_input" not in raw_record
    assert "token" not in raw_record.lower()


def test_complete_github_pr_wait_state(tmp_path: Path) -> None:
    """Terminal PR wait state stores compact result data."""

    registry = WaitRegistry(tmp_path)
    record = register_wait(registry, tmp_path)

    completed = registry.complete_github_pr(record, failed_pr_result(), now=LATER)

    assert completed.status == WAIT_STATUS_READY
    assert completed.terminal_result == "FAIL"
    assert completed.last_observed_state is not None
    assert completed.last_observed_state["completed"] is True
    assert registry.read(record.wait_id) == completed


def test_complete_github_pr_wait_resume_text(tmp_path: Path) -> None:
    """Terminal PR wait state renders continuation context."""

    registry = WaitRegistry(tmp_path)
    record = register_wait(registry, tmp_path)

    completed = registry.complete_github_pr(record, failed_pr_result(), now=LATER)
    resume_text = render_resume_text(completed)

    assert "Result: FAIL" in completed.resume_message
    assert "GitHub check: verify (failure)" in resume_text
    assert "PR checks reached FAIL for PR #291" in resume_text


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


def register_wait(registry: WaitRegistry, root: Path) -> WaitRecord:
    """Register one deterministic GitHub PR wait for tests."""

    return registry.register_github_pr(
        RegisterGitHubPrWait(
            root=root,
            pr_number="291",
            repo="douglasmonsky/agent-maintainer",
            platform="codex",
            branch="codex/background-wait",
            head_sha="abc123",
            interval_seconds=INTERVAL_SECONDS,
            timeout_seconds=TIMEOUT_SECONDS,
            now=NOW,
        ),
    )


def wait_record_path(root: Path, record: WaitRecord) -> Path:
    """Return path to one wait registry record."""

    return root / ".verify-logs" / "waits" / f"{record.wait_id}.json"


def failed_pr_result() -> GitHubPrWaitResult:
    """Return a deterministic failed PR result."""

    return GitHubPrWaitResult(
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
