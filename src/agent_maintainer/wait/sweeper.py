"""Background sweeper for durable wait records."""

from __future__ import annotations

import datetime as dt
import time
from collections.abc import Callable
from dataclasses import dataclass

from agent_maintainer.runtime_events.waiting import WaitRuntimeEvents
from agent_maintainer.wait import (
    broker,
    github,
    github_pr,
)
from agent_maintainer.wait import (
    handlers as wait_handlers,
)
from agent_maintainer.wait import (
    registry as wait_registry,
)
from agent_waits import watcher_state as wait_watcher_state
from agent_waits.notifications import claim_terminal_observation

Sleep = Callable[[int], None]
DetachedWatcher = broker.DetachedWatcher
start_wait_watcher = broker.start_wait_watcher


@dataclass(frozen=True)
class SweepSummary:
    """Summary from one wait registry sweep."""

    checked: int
    updated: int
    pending: int
    ready: int


@dataclass(frozen=True)
class CleanupSummary:
    """Summary of stale wait cleanup."""

    expired_ready: int


def sweep_once(
    registry: wait_registry.WaitRegistry,
    *,
    query_checks: github_pr.QueryPrChecks | None = None,
    query_run: github.QueryRun | None = None,
    query_verifier: wait_handlers.VerifierQuery | None = None,
    now: dt.datetime | None = None,
) -> SweepSummary:
    """Poll pending waits once without printing pending chatter."""

    checked = 0
    updated = 0
    queries = wait_handlers.WaitQueries(
        query_pr_checks=query_checks,
        query_github_run=query_run,
        query_verifier=query_verifier,
    )
    for record in _pending_records(registry):
        checked += 1
        before = registry.read(record.wait_id)
        after = sweep_record(registry, before, queries=queries, now=now)
        if after != before:
            updated += 1
    records = wait_registry.wait_records(registry)
    return SweepSummary(
        checked=checked,
        updated=updated,
        pending=sum(1 for item in records if item.status == wait_registry.WAIT_STATUS_PENDING),
        ready=sum(1 for item in records if item.ready),
    )


def sweep_record(
    registry: wait_registry.WaitRegistry,
    record: wait_registry.WaitRecord,
    *,
    queries: wait_handlers.WaitQueries | None = None,
    now: dt.datetime | None = None,
) -> wait_registry.WaitRecord:
    """Poll one wait record once and persist meaningful state changes."""

    if record.status != wait_registry.WAIT_STATUS_PENDING:
        return record
    if _expired(record, now):
        completed = registry.complete(
            record,
            terminal_result=wait_registry.RESULT_TIMEOUT,
            resume_message="",
            state_data={"timed_out": True},
            now=now,
        )
    else:
        effective_queries = queries or wait_handlers.WaitQueries()
        completed = wait_handlers.handler_for(record.kind).poll_once(
            registry,
            record,
            queries=effective_queries,
            now=now,
        )
    return _emit_terminal_observed(registry, completed, now=now)


def sweep_ready_notifications(
    registry: wait_registry.WaitRegistry,
    *,
    query_checks: github_pr.QueryPrChecks | None = None,
    query_run: github.QueryRun | None = None,
    query_verifier: wait_handlers.VerifierQuery | None = None,
    now: dt.datetime | None = None,
) -> tuple[wait_registry.WaitRecord, ...]:
    """Sweep once and claim repo-heartbeat ready records."""

    sweep_once(
        registry,
        query_checks=query_checks,
        query_run=query_run,
        query_verifier=query_verifier,
        now=now,
    )
    return registry.claim_ready_for_notification(now=now)


def cleanup_waits(
    registry: wait_registry.WaitRegistry,
    *,
    ready_older_than_seconds: int,
    now: dt.datetime | None = None,
) -> CleanupSummary:
    """Expire stale ready waits that should no longer notify."""

    expired = wait_registry.expire_ready_records(
        registry,
        older_than_seconds=ready_older_than_seconds,
        now=now,
    )
    return CleanupSummary(expired_ready=len(expired))


def watch_wait(
    registry: wait_registry.WaitRegistry,
    wait_id: str,
    *,
    query_checks: github_pr.QueryPrChecks | None = None,
    sleep: Sleep = time.sleep,
    now: dt.datetime | None = None,
) -> wait_registry.WaitRecord:
    """Watch one wait until terminal resume record is ready."""

    queries = wait_handlers.WaitQueries(
        query_pr_checks=query_checks,
    )
    while True:
        record = registry.read(wait_id)
        if record.ready:
            return record
        record = wait_watcher_state.mark_watcher_poll(registry, wait_id, now=now)
        if record.ready:
            return record
        updated = sweep_record(registry, record, queries=queries, now=now)
        if updated.ready:
            return updated
        sleep(updated.interval_seconds)


def _pending_records(registry: wait_registry.WaitRegistry) -> tuple[wait_registry.WaitRecord, ...]:
    return tuple(
        item
        for item in wait_registry.wait_records(registry)
        if item.status == wait_registry.WAIT_STATUS_PENDING
    )


def _expired(record: wait_registry.WaitRecord, now: dt.datetime | None) -> bool:
    deadline = dt.datetime.fromisoformat(record.deadline_at.replace("Z", "+00:00"))
    current = now or dt.datetime.now(dt.UTC)
    return current.astimezone(dt.UTC) >= deadline


def _emit_terminal_observed(
    registry: wait_registry.WaitRegistry,
    record: wait_registry.WaitRecord,
    *,
    now: dt.datetime | None,
) -> wait_registry.WaitRecord:
    if not record.ready:
        return record
    observed = claim_terminal_observation(registry, record.wait_id, now=now)
    if observed is None:
        return registry.read(record.wait_id)
    WaitRuntimeEvents.create(
        target_kind=observed.kind,
        target_id=observed.target_id,
    ).ready(
        wait_id=observed.wait_id,
        result=observed.terminal_result,
    )
    return observed
