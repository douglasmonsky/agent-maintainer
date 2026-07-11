"""Privacy-safe lifecycle metadata for durable wait watchers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Final

from agent_waits import constants as wait_constants
from agent_waits.record_lock import wait_record_lock
from agent_waits.registry import (
    WaitRecord,
    WaitRegistry,
    format_timestamp,
    parse_timestamp,
    wait_records,
    write_record,
)

WATCHER_STRATEGY_KEY: Final = "watcher_strategy"
WATCHER_PID_KEY: Final = "watcher_pid"
WATCHER_STARTED_AT_KEY: Final = "watcher_started_at"
WATCHER_LAST_POLL_AT_KEY: Final = "watcher_last_poll_at"
WATCHER_ERROR_KEY: Final = "watcher_error_code"
WATCHER_REPAIR_CLAIMED_AT_KEY: Final = "watcher_repair_claimed_at"
WATCHER_REPAIRING: Final = "repairing"
WATCHER_FAILURE_CODES: Final = frozenset(
    ("launchd_required", "watcher_start_failed", "watcher_repair_failed"),
)


@dataclass(frozen=True)
class WatcherState:
    """Parsed non-sensitive watcher lifecycle facts."""

    strategy: str = ""
    pid: int | None = None
    started_at: str = ""
    last_poll_at: str = ""
    error_code: str = ""
    repair_claimed_at: str = ""


@dataclass(frozen=True)
class _MetadataPatch:
    updates: dict[str, object]
    remove: tuple[str, ...] = ()
    clear_failure: bool = False


def watcher_state(record: WaitRecord) -> WatcherState:
    """Return bounded watcher metadata from one wait record."""

    metadata = record.metadata or {}
    pid = metadata.get(WATCHER_PID_KEY)
    return WatcherState(
        strategy=_text(metadata.get(WATCHER_STRATEGY_KEY)),
        pid=pid if isinstance(pid, int) and pid > 0 else None,
        started_at=_text(metadata.get(WATCHER_STARTED_AT_KEY)),
        last_poll_at=_text(metadata.get(WATCHER_LAST_POLL_AT_KEY)),
        error_code=_text(metadata.get(WATCHER_ERROR_KEY)),
        repair_claimed_at=_text(metadata.get(WATCHER_REPAIR_CLAIMED_AT_KEY)),
    )


def mark_watcher_started(
    registry: WaitRegistry,
    record: WaitRecord,
    *,
    strategy: str,
    pid: int | None,
    now: datetime | None = None,
) -> WaitRecord:
    """Persist watcher start facts without commands, environment, or payloads."""

    started_at = format_timestamp(now)
    updates: dict[str, object] = {
        WATCHER_STRATEGY_KEY: strategy,
        WATCHER_STARTED_AT_KEY: started_at,
        WATCHER_LAST_POLL_AT_KEY: started_at,
    }
    if pid is not None:
        updates[WATCHER_PID_KEY] = pid
    remove = (WATCHER_PID_KEY,) if pid is None else ()
    return _update_metadata(
        registry,
        record.wait_id,
        _MetadataPatch(updates, remove=remove, clear_failure=True),
        now=now,
    )


def mark_watcher_poll(
    registry: WaitRegistry,
    wait_id: str,
    *,
    now: datetime | None = None,
) -> WaitRecord:
    """Persist one watcher poll timestamp while the wait remains pending."""

    return _update_metadata(
        registry,
        wait_id,
        _MetadataPatch({WATCHER_LAST_POLL_AT_KEY: format_timestamp(now)}),
        now=now,
    )


def mark_watcher_failed(
    registry: WaitRegistry,
    record: WaitRecord,
    *,
    error_code: str,
    now: datetime | None = None,
) -> WaitRecord:
    """Persist only a fixed watcher failure code."""

    return _update_metadata(
        registry,
        record.wait_id,
        _MetadataPatch(
            {WATCHER_STRATEGY_KEY: "failed", WATCHER_ERROR_KEY: _safe_code(error_code)},
            remove=(WATCHER_PID_KEY,),
        ),
        now=now,
    )


def watcher_repair_eligible(
    record: WaitRecord,
    *,
    active: bool,
    stale_after_seconds: int,
    now: datetime | None = None,
) -> bool:
    """Return whether a pending watcher is stale, inactive, and repairable."""

    if record.status != wait_constants.WAIT_STATUS_PENDING or active:
        return False
    state = watcher_state(record)
    if state.strategy == WATCHER_REPAIRING:
        reference = state.repair_claimed_at or record.updated_at
    else:
        reference = state.last_poll_at or state.started_at or record.created_at
    age = (parse_timestamp(format_timestamp(now)) - parse_timestamp(reference)).total_seconds()
    return 0 <= stale_after_seconds <= age


def claim_watcher_repair(
    registry: WaitRegistry,
    wait_id: str,
    *,
    active_check: Callable[[WatcherState], bool],
    stale_after_seconds: int,
    now: datetime | None = None,
) -> WaitRecord | None:
    """Recheck liveness and atomically claim a stale watcher for replacement."""

    with wait_record_lock(registry.waits_dir, wait_id):
        current = registry.read(wait_id)
        if not watcher_repair_eligible(
            current,
            active=active_check(watcher_state(current)),
            stale_after_seconds=stale_after_seconds,
            now=now,
        ):
            return None
        claimed_at = format_timestamp(now)
        metadata = dict(current.metadata or {})
        metadata[WATCHER_STRATEGY_KEY] = WATCHER_REPAIRING
        metadata[WATCHER_REPAIR_CLAIMED_AT_KEY] = claimed_at
        metadata.pop(WATCHER_PID_KEY, None)
        claimed = replace(current, updated_at=claimed_at, metadata=metadata)
        write_record(registry.waits_dir, claimed)
        return claimed


def mark_pending_watcher_polls(
    registry: WaitRegistry,
    *,
    now: datetime | None = None,
) -> None:
    """Record daemon poll time for every wait that remains pending."""

    for record in wait_records(registry):
        if record.status == wait_constants.WAIT_STATUS_PENDING:
            mark_watcher_poll(registry, record.wait_id, now=now)


def _update_metadata(
    registry: WaitRegistry,
    wait_id: str,
    patch: _MetadataPatch,
    *,
    now: datetime | None = None,
) -> WaitRecord:
    with wait_record_lock(registry.waits_dir, wait_id):
        current = registry.read(wait_id)
        if current.status != wait_constants.WAIT_STATUS_PENDING:
            return current
        metadata = dict(current.metadata or {})
        metadata.update(patch.updates)
        for key in patch.remove:
            metadata.pop(key, None)
        if patch.clear_failure:
            metadata.pop(WATCHER_ERROR_KEY, None)
            metadata.pop(WATCHER_REPAIR_CLAIMED_AT_KEY, None)
        updated = replace(current, updated_at=format_timestamp(now), metadata=metadata)
        write_record(registry.waits_dir, updated)
        return updated


def _safe_code(value: str) -> str:
    return value if value in WATCHER_FAILURE_CODES else "watcher_failed"


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""
