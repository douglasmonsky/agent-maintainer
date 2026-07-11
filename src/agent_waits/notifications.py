"""Exactly-once terminal notification transitions for durable waits."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from typing import Final

from agent_waits import constants as wait_constants
from agent_waits.record_lock import wait_record_lock
from agent_waits.registry import (
    WaitRecord,
    WaitRegistry,
    _parse_timestamp,
    _timestamp,
    _write_record,
    wait_records,
)

NOTIFICATION_OUTCOME_FAILED: Final = "failed"
NOTIFICATION_OUTCOME_RESUMED: Final = "resumed"
FAILURE_APP_SERVER: Final = "app_server_error"
FAILURE_VISIBLE_WAKE_UNCONFIRMED: Final = "visible_wake_unconfirmed"
FAILURE_LEASE_EXPIRED: Final = "notification_lease_expired"
FAILURE_GENERIC: Final = "notification_failed"
REGISTRATION_OBSERVED_AT_METADATA: Final = "registration_observed_at"
WATCHER_STARTED_OBSERVED_AT_METADATA: Final = "watcher_started_observed_at"
FALLBACK_USED_OBSERVED_AT_METADATA: Final = "fallback_used_observed_at"
TERMINAL_OBSERVED_AT_METADATA: Final = "terminal_observed_at"
DEFAULT_NOTIFICATION_LEASE_SECONDS: Final = 300
ALLOWED_FAILURE_REASONS: Final = frozenset(
    (FAILURE_APP_SERVER, FAILURE_VISIBLE_WAKE_UNCONFIRMED, FAILURE_LEASE_EXPIRED),
)


def claim_terminal_notification(
    registry: WaitRegistry,
    wait_id: str,
    *,
    now: datetime | None = None,
) -> WaitRecord | None:
    """Atomically claim one ready wait immediately before external notification."""

    with wait_record_lock(registry.waits_dir, wait_id):
        current = registry.read(wait_id)
        if not current.notification_ready:
            return None
        timestamp = _timestamp(now)
        metadata = dict(current.metadata or {})
        metadata["notification_claimed_at"] = timestamp
        claimed = replace(
            current,
            status=wait_constants.WAIT_STATUS_NOTIFYING,
            updated_at=timestamp,
            metadata=metadata,
        )
        _write_record(registry.waits_dir, claimed)
        return claimed


def claim_terminal_observation(
    registry: WaitRegistry,
    wait_id: str,
    *,
    now: datetime | None = None,
) -> WaitRecord | None:
    """Claim one terminal-observed event without changing lifecycle timing."""

    return _claim_observation(
        registry,
        wait_id,
        metadata_key=TERMINAL_OBSERVED_AT_METADATA,
        eligible=lambda record: record.ready,
        now=now,
    )


def claim_registration_observation(
    registry: WaitRegistry,
    wait_id: str,
    *,
    now: datetime | None = None,
) -> WaitRecord | None:
    """Claim the single registration event for one durable wait."""

    return _claim_observation(
        registry,
        wait_id,
        metadata_key=REGISTRATION_OBSERVED_AT_METADATA,
        eligible=lambda _record: True,
        now=now,
    )


def claim_watcher_started_observation(
    registry: WaitRegistry,
    wait_id: str,
    *,
    now: datetime | None = None,
) -> WaitRecord | None:
    """Claim the first successful watcher-started event for one wait."""

    return _claim_observation(
        registry,
        wait_id,
        metadata_key=WATCHER_STARTED_OBSERVED_AT_METADATA,
        eligible=lambda _record: True,
        now=now,
    )


def claim_fallback_used_observation(
    registry: WaitRegistry,
    wait_id: str,
    *,
    now: datetime | None = None,
) -> WaitRecord | None:
    """Claim the first rendered model-turn fallback for one wait."""

    return _claim_observation(
        registry,
        wait_id,
        metadata_key=FALLBACK_USED_OBSERVED_AT_METADATA,
        eligible=lambda _record: True,
        now=now,
    )


def _claim_observation(
    registry: WaitRegistry,
    wait_id: str,
    *,
    metadata_key: str,
    eligible: Callable[[WaitRecord], bool],
    now: datetime | None,
) -> WaitRecord | None:
    with wait_record_lock(registry.waits_dir, wait_id):
        current = registry.read(wait_id)
        metadata = dict(current.metadata or {})
        if not eligible(current) or metadata_key in metadata:
            return None
        metadata[metadata_key] = _timestamp(now)
        observed = replace(current, metadata=metadata)
        _write_record(registry.waits_dir, observed)
        return observed


def finish_terminal_notification(
    registry: WaitRegistry,
    wait_id: str,
    *,
    outcome: str,
    failure_reason: str = "",
    now: datetime | None = None,
) -> WaitRecord:
    """Finish a claimed notification without permitting implicit retries."""

    with wait_record_lock(registry.waits_dir, wait_id):
        current = registry.read(wait_id)
        if current.status != wait_constants.WAIT_STATUS_NOTIFYING:
            return current
        finished = _finished_notification(
            current,
            outcome=outcome,
            failure_reason=failure_reason,
            now=now,
        )
        _write_record(registry.waits_dir, finished)
        return finished


def repair_stale_notifications(
    registry: WaitRegistry,
    *,
    lease_seconds: int,
    wait_id: str | None = None,
    now: datetime | None = None,
) -> tuple[WaitRecord, ...]:
    """Fail closed any abandoned notification claims older than the lease."""

    if lease_seconds < 0:
        return ()
    repaired: list[WaitRecord] = []
    for record in wait_records(registry):
        if wait_id is not None and record.wait_id != wait_id:
            continue
        if record.status != wait_constants.WAIT_STATUS_NOTIFYING:
            continue
        with wait_record_lock(registry.waits_dir, record.wait_id):
            current = registry.read(record.wait_id)
            if not _stale_notification(
                current,
                lease_seconds=lease_seconds,
                now=now,
            ):
                continue
            finished = _finished_notification(
                current,
                outcome=NOTIFICATION_OUTCOME_FAILED,
                failure_reason=FAILURE_LEASE_EXPIRED,
                now=now,
            )
            _write_record(registry.waits_dir, finished)
            repaired.append(finished)
    return tuple(repaired)


def _finished_notification(
    current: WaitRecord,
    *,
    outcome: str,
    failure_reason: str,
    now: datetime | None,
) -> WaitRecord:
    timestamp = _timestamp(now)
    metadata = dict(current.metadata or {})
    metadata["notification_finished_at"] = timestamp
    if outcome == NOTIFICATION_OUTCOME_RESUMED:
        status = wait_constants.WAIT_STATUS_RESUMED
        metadata.pop("notification_failure_reason", None)
    else:
        status = wait_constants.WAIT_STATUS_NOTIFY_FAILED
        metadata["notification_failure_reason"] = _safe_failure_reason(failure_reason)
    return replace(
        current,
        status=status,
        updated_at=timestamp,
        metadata=metadata,
    )


def _stale_notification(
    record: WaitRecord,
    *,
    lease_seconds: int,
    now: datetime | None,
) -> bool:
    if record.status != wait_constants.WAIT_STATUS_NOTIFYING:
        return False
    current_time = _parse_timestamp(_timestamp(now))
    age = (current_time - _parse_timestamp(record.updated_at)).total_seconds()
    return age >= lease_seconds


def _safe_failure_reason(reason: str) -> str:
    return reason if reason in ALLOWED_FAILURE_REASONS else FAILURE_GENERIC
