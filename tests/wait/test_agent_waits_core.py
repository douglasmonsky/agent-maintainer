"""Tests reusable wait orchestration primitives."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from agent_waits.broker import (
    BackgroundWaitRegistration,
    heartbeat_prompt,
    render_background_registration_text,
)
from agent_waits.registry import (
    RESULT_PENDING,
    RegisterWait,
    WaitRegistry,
    render_wait_record_text,
    wait_record_from_dict,
)

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
    assert "target: run-123" in render_wait_record_text(record)


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
