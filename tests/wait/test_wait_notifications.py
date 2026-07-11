"""Tests atomic terminal notification lifecycle."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from threading import Barrier

from agent_waits.constants import (
    WAIT_STATUS_NOTIFY_FAILED,
    WAIT_STATUS_NOTIFYING,
    WAIT_STATUS_READY,
)
from agent_waits.notifications import (
    FAILURE_APP_SERVER,
    FAILURE_LEASE_EXPIRED,
    NOTIFICATION_OUTCOME_FAILED,
    claim_terminal_notification,
    finish_terminal_notification,
    repair_stale_notifications,
)
from agent_waits.registry import RegisterWait, WaitRecord, WaitRegistry

NOW = datetime.fromisoformat("2026-07-10T22:00:00+00:00")
LATER = datetime.fromisoformat("2026-07-10T22:02:00+00:00")


def test_terminal_notification_can_be_claimed_only_once(tmp_path: Path) -> None:
    """Sequential claimers model the per-record lock's exactly-once decision."""

    registry = WaitRegistry(tmp_path)
    record = ready_wait(registry, tmp_path)

    first = claim_terminal_notification(registry, record.wait_id, now=NOW)
    second = claim_terminal_notification(registry, record.wait_id, now=NOW)

    assert first is not None
    assert first.status == WAIT_STATUS_NOTIFYING
    assert second is None
    assert registry.read(record.wait_id).status == WAIT_STATUS_NOTIFYING


def test_concurrent_terminal_claimers_produce_one_winner(tmp_path: Path) -> None:
    """Per-record locking prevents parallel watchers from double-notifying."""

    registry = WaitRegistry(tmp_path)
    record = ready_wait(registry, tmp_path)
    barrier = Barrier(2)

    def claim() -> WaitRecord | None:
        barrier.wait()
        return claim_terminal_notification(registry, record.wait_id, now=NOW)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(lambda _index: claim(), range(2)))

    assert sum(result is not None for result in results) == 1


def test_stale_pending_poll_cannot_overwrite_notification_claim(tmp_path: Path) -> None:
    """A late observer using an old pending object preserves the newer state."""

    registry = WaitRegistry(tmp_path)
    pending = registry.register(
        RegisterWait(root=tmp_path, kind="verifier", target_id="run-1", now=NOW),
    )
    ready = registry.complete(
        pending,
        terminal_result="PASS",
        resume_message="done",
        state_data={"status": "passed"},
        now=NOW,
    )
    assert claim_terminal_notification(registry, ready.wait_id, now=NOW) is not None

    observed = registry.observe(pending, {"status": "running"}, now=LATER)
    completed = registry.complete(
        pending,
        terminal_result="PASS",
        resume_message="stale",
        state_data={"status": "passed"},
        now=LATER,
    )

    assert observed.status == WAIT_STATUS_NOTIFYING
    assert completed.status == WAIT_STATUS_NOTIFYING
    assert registry.read(ready.wait_id).status == WAIT_STATUS_NOTIFYING


def test_failed_notification_stays_manually_resumable_without_retry(tmp_path: Path) -> None:
    """Notification failure is ready for a person but not another automatic claim."""

    registry = WaitRegistry(tmp_path)
    record = ready_wait(registry, tmp_path)
    assert claim_terminal_notification(registry, record.wait_id, now=NOW) is not None

    failed = finish_terminal_notification(
        registry,
        record.wait_id,
        outcome=NOTIFICATION_OUTCOME_FAILED,
        failure_reason=FAILURE_APP_SERVER,
        now=LATER,
    )

    assert failed.status == WAIT_STATUS_NOTIFY_FAILED
    assert failed.ready is True
    assert failed.notification_ready is False
    assert failed.metadata is not None
    assert failed.metadata["notification_failure_reason"] == FAILURE_APP_SERVER
    assert claim_terminal_notification(registry, record.wait_id, now=LATER) is None


def test_failure_reason_is_fixed_code_not_private_diagnostic(tmp_path: Path) -> None:
    """Unexpected failure text is replaced rather than persisted."""

    registry = WaitRegistry(tmp_path)
    record = ready_wait(registry, tmp_path)
    assert claim_terminal_notification(registry, record.wait_id, now=NOW) is not None

    failed = finish_terminal_notification(
        registry,
        record.wait_id,
        outcome=NOTIFICATION_OUTCOME_FAILED,
        failure_reason="api-key-private-value",
        now=LATER,
    )
    raw = (registry.waits_dir / failed.path_name).read_text(encoding="utf-8")

    assert "api-key-private-value" not in raw
    assert failed.metadata is not None
    assert failed.metadata["notification_failure_reason"] == "notification_failed"


def test_stale_notification_claim_fails_closed(tmp_path: Path) -> None:
    """An abandoned notification lease becomes manual-only, never retryable."""

    registry = WaitRegistry(tmp_path)
    record = ready_wait(registry, tmp_path)
    assert claim_terminal_notification(registry, record.wait_id, now=NOW) is not None

    repaired = repair_stale_notifications(
        registry,
        lease_seconds=60,
        now=LATER,
    )

    assert len(repaired) == 1
    assert repaired[0].status == WAIT_STATUS_NOTIFY_FAILED
    assert repaired[0].metadata is not None
    assert repaired[0].metadata["notification_failure_reason"] == FAILURE_LEASE_EXPIRED


def ready_wait(registry: WaitRegistry, root: Path) -> WaitRecord:
    record = registry.register(
        RegisterWait(root=root, kind="verifier", target_id="run-1", now=NOW),
    )
    completed = registry.complete(
        record,
        terminal_result="PASS",
        resume_message="done",
        state_data={"status": "passed"},
        now=NOW,
    )
    assert completed.status == WAIT_STATUS_READY
    return completed
