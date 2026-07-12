"""Tests reusable wait orchestration primitives."""

from __future__ import annotations

import json
import shlex
import sys
from datetime import datetime
from pathlib import Path

from agent_waits.broker import (
    CODEX_PLATFORM,
    CODEX_REWAKE_ENV,
    CODEX_THREAD_ID_ENV,
    CODEX_THREAD_ID_OVERRIDE_ENV,
    BackgroundWaitRegistration,
    heartbeat_prompt,
    heartbeat_request_json,
    render_background_registration_text,
    running_in_codex,
)
from agent_waits.constants import (
    RESULT_PASS,
    RESULT_PENDING,
    WAIT_STATUS_EXPIRED_READY,
)
from agent_waits.heartbeat import (
    HEARTBEAT_MODE_METADATA,
    HEARTBEAT_MODE_REPO,
    HEARTBEAT_NOTIFIED_AT_METADATA,
)
from agent_waits.registry import (
    RegisterWait,
    WaitRegistry,
    expire_ready_records,
    wait_record_from_dict,
)
from agent_waits.rendering import render_wait_record_text

NOW = datetime.fromisoformat("2026-07-07T02:00:00+00:00")
FALLBACK_MONITOR_INTERVAL_SECONDS = 120
FALLBACK_MONITOR_MAX_INTERVAL_SECONDS = 1800
LONG_MONITOR_INTERVAL_SECONDS = 3600


def test_running_in_codex_accepts_thread_override() -> None:
    """Explicit thread override marks Codex environment."""

    assert running_in_codex({CODEX_THREAD_ID_ENV: ""}) is False
    assert running_in_codex({CODEX_THREAD_ID_OVERRIDE_ENV: "thread-1"})


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


def test_heartbeat_backoff_caps_large_configured_interval(tmp_path: Path) -> None:
    """Fallback cadence never advertises an interval above its hard cap."""

    record = WaitRegistry(tmp_path).register(
        RegisterWait(
            root=tmp_path,
            kind="verifier",
            target_id="run-long",
            interval_seconds=LONG_MONITOR_INTERVAL_SECONDS,
            now=NOW,
        ),
    )

    request = json.loads(heartbeat_request_json(record, root=tmp_path))
    backoff = request["backoff"]

    assert request["preferred_interval_seconds"] == FALLBACK_MONITOR_MAX_INTERVAL_SECONDS
    assert backoff["initial_interval_seconds"] == FALLBACK_MONITOR_MAX_INTERVAL_SECONDS
    assert backoff["max_interval_seconds"] == FALLBACK_MONITOR_MAX_INTERVAL_SECONDS


def test_default_wait_commands_use_the_running_executable_and_quote_root(
    tmp_path: Path,
) -> None:
    """Default monitor commands remain runnable from roots with spaces."""

    root = tmp_path / "repo root"
    record = WaitRegistry(root).register(
        RegisterWait(root=root, kind="verifier", target_id="run-123", now=NOW),
    )

    request = json.loads(heartbeat_request_json(record, root=root))
    executable = shlex.quote(sys.executable)
    quoted_root = shlex.quote(str(root))
    resume = f"{executable} -m agent_maintainer wait resume {record.wait_id}"

    assert record.resume_instruction == resume
    assert request["sweep_command"] == (
        f"{executable} -m agent_maintainer wait sweep --one {record.wait_id} --root {quoted_root}"
    )
    assert request["resume_command"] == f"{resume} --root {quoted_root}"


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


def test_github_run_identity_ignores_head_sha(tmp_path: Path) -> None:
    """GitHub run waits are keyed by run id and repo, not changing SHA metadata."""

    registry = WaitRegistry(tmp_path)

    first = registry.register(
        RegisterWait(
            root=tmp_path,
            kind="github-run",
            target_id="123",
            repo="douglasmonsky/agent-maintainer",
            head_sha="abc123",
            now=NOW,
        ),
    )
    second = registry.register(
        RegisterWait(
            root=tmp_path,
            kind="github-run",
            target_id="123",
            repo="douglasmonsky/agent-maintainer",
            head_sha="def456",
            now=NOW.replace(minute=1),
        ),
    )

    assert second.wait_id == first.wait_id


def test_verifier_identity_uses_head_sha(tmp_path: Path) -> None:
    """Verifier waits for different repo states do not deduplicate."""

    registry = WaitRegistry(tmp_path)

    first = registry.register(
        RegisterWait(
            root=tmp_path,
            kind="verifier",
            target_id="run-1",
            head_sha="abc123",
            now=NOW,
        ),
    )
    second = registry.register(
        RegisterWait(
            root=tmp_path,
            kind="verifier",
            target_id="run-1",
            head_sha="def456",
            now=NOW.replace(minute=1),
        ),
    )

    assert second.wait_id != first.wait_id


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


def test_expire_ready_records_marks_stale_ready(tmp_path: Path) -> None:
    """Stale ready records expire and cannot trigger future heartbeat claims."""

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

    expired = expire_ready_records(
        registry,
        older_than_seconds=60,
        now=NOW.replace(minute=3),
    )
    second_expired = expire_ready_records(
        registry,
        older_than_seconds=60,
        now=NOW.replace(minute=4),
    )

    expired_record = registry.read(completed.wait_id)
    assert [item.wait_id for item in expired] == [completed.wait_id]
    assert second_expired == ()
    assert expired_record.status == WAIT_STATUS_EXPIRED_READY
    assert expired_record.metadata is not None
    assert expired_record.metadata["expired_reason"] == "ready_ttl"
    assert registry.claim_ready_for_notification(now=NOW.replace(minute=5)) == ()


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
    assert "fallback heartbeat request:" in text
    assert "model-turn fallback: each heartbeat poll consumes a model turn" in text
    assert heartbeat_prompt(record) in text
    request = json.loads(heartbeat_request_json(record, root=tmp_path))
    assert request["scope"] == "wait"
    assert request["on_pending"] == "silent"
    assert request["on_terminal"] == "resume_and_review"
    assert request["fallback_only"] is True
    assert request["preferred_monitor_model"] == "gpt-5.3-codex-spark"
    assert request["preferred_monitor_reasoning"] == "minimal"
    assert request["preferred_interval_seconds"] == FALLBACK_MONITOR_INTERVAL_SECONDS
    assert request["heartbeat_attempt"] == 0
    assert request["backoff"] == {
        "strategy": "exponential",
        "initial_interval_seconds": FALLBACK_MONITOR_INTERVAL_SECONDS,
        "multiplier": 2,
        "max_interval_seconds": FALLBACK_MONITOR_MAX_INTERVAL_SECONDS,
        "reset_on": "terminal_or_new_wait",
    }
    assert request["merge_policy"] == "merge_only_if_satisfactory"
    assert request["sweep_command"].endswith(
        f"wait sweep --one {record.wait_id} --root {tmp_path}",
    )
    assert "targeted wait sweep command" in request["prompt"]
    assert "exponential backoff" in request["prompt"]
    assert "stop the heartbeat" in request["prompt"]
    assert record.wait_id not in request["prompt"]


def test_background_registration_keeps_fallback_until_visible_rewake_is_proven(
    tmp_path: Path,
) -> None:
    """An app-server candidate alone does not suppress recoverable fallback."""

    record = WaitRegistry(tmp_path).register(
        RegisterWait(
            root=tmp_path,
            kind="verifier",
            target_id="run-123",
            platform=CODEX_PLATFORM,
            now=NOW,
        ),
    )
    text = render_background_registration_text(
        BackgroundWaitRegistration(record=record, watcher_started=True),
        env={CODEX_REWAKE_ENV: "1", CODEX_THREAD_ID_ENV: "thread-1"},
        backend_available=True,
    )

    assert f"Result: {RESULT_PENDING}" in text
    assert "pending polls stay outside model turns" in text
    assert "terminal rewake: enabled" not in text
    assert "manual resume:" in text
    assert "codex_heartbeat_wait" in text
    assert "model-turn fallback" in text


def test_background_registration_keeps_heartbeat_without_rewake_backend(
    tmp_path: Path,
) -> None:
    """Codex env flags alone do not suppress the fallback heartbeat."""

    record = WaitRegistry(tmp_path).register(
        RegisterWait(
            root=tmp_path,
            kind="verifier",
            target_id="run-123",
            platform=CODEX_PLATFORM,
            now=NOW,
        ),
    )
    text = render_background_registration_text(
        BackgroundWaitRegistration(record=record, watcher_started=True),
        env={CODEX_REWAKE_ENV: "1", CODEX_THREAD_ID_ENV: "thread-1"},
        backend_available=False,
    )

    assert "fallback heartbeat request:" in text
    assert "codex_heartbeat_wait" in text
    assert "terminal rewake: enabled" not in text


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
