"""Tests atomic terminal notification lifecycle."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from threading import Barrier

import pytest

from agent_waits import notifications as notifications_module
from agent_waits.constants import (
    WAIT_STATUS_NOTIFY_FAILED,
    WAIT_STATUS_NOTIFYING,
    WAIT_STATUS_READY,
)
from agent_waits.notifications import (
    FAILURE_APP_SERVER,
    FAILURE_LEASE_EXPIRED,
    NOTIFICATION_OUTCOME_FAILED,
    TERMINAL_OBSERVED_AT_METADATA,
    claim_terminal_notification,
    claim_terminal_observation,
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

    def claim(_index: int) -> WaitRecord | None:
        barrier.wait()
        return claim_terminal_notification(registry, record.wait_id, now=NOW)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(claim, range(2)))

    assert sum(result is not None for result in results) == 1


def test_terminal_observation_can_be_claimed_once(tmp_path: Path) -> None:
    """Terminal telemetry has one durable claim across parallel sweepers."""

    registry = WaitRegistry(tmp_path)
    record = ready_wait(registry, tmp_path)
    barrier = Barrier(2)

    def claim(_index: int) -> WaitRecord | None:
        barrier.wait()
        return claim_terminal_observation(registry, record.wait_id, now=NOW)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(claim, range(2)))

    assert sum(result is not None for result in results) == 1
    persisted = registry.read(record.wait_id)
    assert persisted.metadata is not None
    observed_at = persisted.metadata[TERMINAL_OBSERVED_AT_METADATA]
    assert isinstance(observed_at, str)
    assert observed_at.startswith("2026-07-10")


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


def test_parallel_stale_repairs_report_one_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only the process that owns the locked transition reports its event."""

    registry = WaitRegistry(tmp_path)
    record = ready_wait(registry, tmp_path)
    assert claim_terminal_notification(registry, record.wait_id, now=NOW) is not None
    barrier = Barrier(2)
    original_wait_records = notifications_module.wait_records

    def synchronized_records(active_registry: WaitRegistry) -> tuple[WaitRecord, ...]:
        records = original_wait_records(active_registry)
        barrier.wait()
        return records

    monkeypatch.setattr(notifications_module, "wait_records", synchronized_records)

    def repair(_index: int) -> tuple[WaitRecord, ...]:
        return repair_stale_notifications(registry, lease_seconds=60, now=LATER)

    with ThreadPoolExecutor(max_workers=2) as executor:
        repaired = tuple(executor.map(repair, range(2)))

    assert sum(len(records) for records in repaired) == 1
    assert registry.read(record.wait_id).status == WAIT_STATUS_NOTIFY_FAILED


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
