"""Background sweeper for durable wait records."""

from __future__ import annotations

import subprocess  # nosec B404
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from agent_maintainer.wait import handlers as wait_handlers
from agent_maintainer.wait import registry as wait_registry
from agent_maintainer.wait.github import QueryRun
from agent_maintainer.wait.github_pr import QueryPrChecks

Sleep = Callable[[int], None]


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


@dataclass(frozen=True)
class DetachedWatcher:
    """Detached watcher metadata."""

    command: tuple[str, ...]


def sweep_once(
    registry: wait_registry.WaitRegistry,
    *,
    query_checks: QueryPrChecks | None = None,
    query_run: QueryRun | None = None,
    query_verifier: wait_handlers.VerifierQuery | None = None,
    now: datetime | None = None,
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
    now: datetime | None = None,
) -> wait_registry.WaitRecord:
    """Poll one wait record once and persist meaningful state changes."""

    if record.status != wait_registry.WAIT_STATUS_PENDING:
        return record
    if _expired(record, now):
        return registry.complete(
            record,
            terminal_result=wait_registry.RESULT_TIMEOUT,
            resume_message="",
            state_data={"timed_out": True},
            now=now,
        )
    effective_queries = queries or wait_handlers.WaitQueries()
    return wait_handlers.handler_for(record.kind).poll_once(
        registry,
        record,
        queries=effective_queries,
        now=now,
    )


def sweep_ready_notifications(
    registry: wait_registry.WaitRegistry,
    *,
    query_checks: QueryPrChecks | None = None,
    query_run: QueryRun | None = None,
    query_verifier: wait_handlers.VerifierQuery | None = None,
    now: datetime | None = None,
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
    now: datetime | None = None,
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
    query_checks: QueryPrChecks | None = None,
    sleep: Sleep = time.sleep,
    now: datetime | None = None,
) -> wait_registry.WaitRecord:
    """Watch one wait until terminal resume record is ready."""

    queries = wait_handlers.WaitQueries(
        query_pr_checks=query_checks,
    )
    while True:
        record = registry.read(wait_id)
        if record.ready:
            return record
        updated = sweep_record(registry, record, queries=queries, now=now)
        if updated.ready:
            return updated
        sleep(updated.interval_seconds)


def start_wait_watcher(
    root: Path,
    wait_id: str,
    *,
    python_executable: str = sys.executable,
) -> DetachedWatcher:
    """Start a detached local watcher process for one wait record."""

    command = (
        python_executable,
        "-m",
        "agent_maintainer",
        "wait",
        "sweep",
        "--watch",
        wait_id,
        "--root",
        str(root),
    )
    subprocess.Popen(  # nosec B603 # pylint: disable=consider-using-with
        list(command),
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        start_new_session=True,
    )
    return DetachedWatcher(command=command)


def _pending_records(registry: wait_registry.WaitRegistry) -> tuple[wait_registry.WaitRecord, ...]:
    return tuple(
        item
        for item in wait_registry.wait_records(registry)
        if item.status == wait_registry.WAIT_STATUS_PENDING
    )


def _expired(record: wait_registry.WaitRecord, now: datetime | None) -> bool:
    deadline = datetime.fromisoformat(record.deadline_at.replace("Z", "+00:00"))
    current = now or datetime.now(UTC)
    return current.astimezone(UTC) >= deadline
