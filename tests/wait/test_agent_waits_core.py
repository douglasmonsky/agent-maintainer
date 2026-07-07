"""Tests reusable wait orchestration primitives."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from agent_waits.broker import (
    BackgroundWaitRegistration,
    heartbeat_prompt,
    heartbeat_request_json,
    render_background_registration_text,
)
from agent_waits.constants import RESULT_PASS, RESULT_PENDING
from agent_waits.heartbeat import (
    HEARTBEAT_MODE_METADATA,
    HEARTBEAT_MODE_REPO,
    HEARTBEAT_NOTIFIED_AT_METADATA,
)
from agent_waits.registry import (
    RegisterWait,
    WaitRegistry,
    wait_record_from_dict,
)
from agent_waits.rendering import render_wait_record_text

NOW = datetime.fromisoformat("2026-07-07T02:00:00+00:00")


def test_generic_wait_registry_writes_target_id(tmp_path: Path) -> None:
    """Generic wait records persist neutral target metadata."""

    registry = WaitRegistry(tmp_path)
    record = registry.register(
        RegisterWait(
            root=tmp_path,
            kind="verifier",
            target_id="run-123",
            platform="codex",
            interval_seconds=5,
            timeout_seconds=60,
            now=NOW,
        ),
    )

    payload = json.loads((registry.waits_dir / f"{record.wait_id}.json").read_text())

    assert payload["target_id"] == "run-123"
    assert "pr_number" not in payload
    assert record.wait_id == "verifier-run-123-20260707T020000Z"
    assert record.metadata == {HEARTBEAT_MODE_METADATA: HEARTBEAT_MODE_REPO}
    assert "target: run-123" in render_wait_record_text(record)


def test_register_deduplicates_active_wait_identity(tmp_path: Path) -> None:
    """Repeated active wait registrations reuse durable wait identity."""

    registry = WaitRegistry(tmp_path)
    first = registry.register(
        RegisterWait(
            root=tmp_path,
            kind="github-pr",
            target_id="291",
            repo="douglasmonsky/agent-maintainer",
            head_sha="abc123",
            now=NOW,
        ),
    )
    duplicate = registry.register(
        RegisterWait(
            root=tmp_path,
            kind="github-pr",
            target_id="291",
            repo="douglasmonsky/agent-maintainer",
            head_sha="abc123",
            now=NOW.replace(minute=1),
        ),
    )

    assert duplicate.wait_id == first.wait_id
    assert len(tuple(registry.waits_dir.glob("*.json"))) == 1


def test_register_deduplicates_active_wait_without_repo(tmp_path: Path) -> None:
    """Wait identity does not require a GitHub repo."""

    registry = WaitRegistry(tmp_path)
    first = registry.register(
        RegisterWait(root=tmp_path, kind="verifier", target_id="run-123", now=NOW),
    )
    duplicate = registry.register(
        RegisterWait(
            root=tmp_path,
            kind="verifier",
            target_id="run-123",
            now=NOW.replace(minute=1),
        ),
    )

    assert duplicate.wait_id == first.wait_id
    assert len(tuple(registry.waits_dir.glob("*.json"))) == 1


def test_resumed_wait_identity_can_register_again(tmp_path: Path) -> None:
    """Consumed wait records do not block a later matching registration."""

    registry = WaitRegistry(tmp_path)
    first = registry.register(
        RegisterWait(root=tmp_path, kind="github-run", target_id="123", now=NOW),
    )
    registry.mark_resumed(first, now=NOW.replace(minute=1))

    second = registry.register(
        RegisterWait(
            root=tmp_path,
            kind="github-run",
            target_id="123",
            now=NOW.replace(minute=2),
        ),
    )

    assert second.wait_id != first.wait_id


def test_claim_ready_for_notification_marks_once(tmp_path: Path) -> None:
    """Repo heartbeat claims ready records only once."""

    registry = WaitRegistry(tmp_path)
    record = registry.register(
        RegisterWait(root=tmp_path, kind="verifier", target_id="run-123", now=NOW),
    )
    completed = registry.complete(
        record,
        terminal_result=RESULT_PASS,
        resume_message="done",
        state_data={"ok": True},
        now=NOW.replace(minute=1),
    )

    claimed = registry.claim_ready_for_notification(now=NOW.replace(minute=2))
    second_claim = registry.claim_ready_for_notification(now=NOW.replace(minute=3))

    assert [item.wait_id for item in claimed] == [completed.wait_id]
    assert claimed[0].metadata is not None
    assert HEARTBEAT_NOTIFIED_AT_METADATA in claimed[0].metadata
    assert second_claim == ()


def test_legacy_pr_number_records_still_read() -> None:
    """Old GitHub PR records without target_id remain readable."""

    record = wait_record_from_dict(
        {
            "schema_version": 1,
            "wait_id": "github-pr-291-20260707T020000Z",
            "kind": "github-pr",
            "status": "pending",
            "pr_number": "291",
            "repo": "douglasmonsky/agent-maintainer",
            "platform": "codex",
            "branch": "",
            "head_sha": "",
            "interval_seconds": 20,
            "timeout_seconds": 3600,
            "created_at": "2026-07-07T02:00:00Z",
            "updated_at": "2026-07-07T02:00:00Z",
            "deadline_at": "2026-07-07T03:00:00Z",
            "last_observed_state": None,
            "terminal_result": "",
            "resume_instruction": "python -m agent_maintainer wait resume github-pr-291",
            "resume_message": "",
        },
    )

    assert record.target_id == "291"
    assert record.pr_number == "291"
    assert record.as_dict()["pr_number"] == "291"


def test_background_registration_text_is_generic(tmp_path: Path) -> None:
    """Background registration rendering works for non-PR wait records."""

    record = WaitRegistry(tmp_path).register(
        RegisterWait(root=tmp_path, kind="verifier", target_id="run-123", now=NOW),
    )
    text = render_background_registration_text(
        BackgroundWaitRegistration(record=record, watcher_started=True),
    )

    assert f"Result: {RESULT_PENDING}" in text
    assert "verifier wait registered for run-123" in text
    assert "watcher: started" in text
    assert "heartbeat request:" in text
    assert heartbeat_prompt(record) in text
    request = json.loads(heartbeat_request_json(record, root=tmp_path))
    assert request["scope"] == "repo"
    assert request["sweep_command"].endswith("wait heartbeat --root " + str(tmp_path))
    assert "repo wait heartbeat sweep command" in request["prompt"]
    assert record.wait_id not in request["prompt"]


def test_background_registration_text_reflects_ready_result(tmp_path: Path) -> None:
    """Duplicate handoffs for ready waits do not render as pending."""

    registry = WaitRegistry(tmp_path)
    record = registry.register(
        RegisterWait(root=tmp_path, kind="verifier", target_id="run-123", now=NOW),
    )
    completed = registry.complete(
        record,
        terminal_result=RESULT_PASS,
        resume_message="done",
        state_data={"ok": True},
        now=NOW.replace(minute=1),
    )

    text = render_background_registration_text(
        BackgroundWaitRegistration(record=completed, watcher_started=False),
    )

    assert f"Result: {RESULT_PASS}" in text
    assert f"Result: {RESULT_PENDING}" not in text
