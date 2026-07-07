"""Background sweeper for durable wait records."""

from __future__ import annotations

import json
import subprocess  # nosec B404
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from agent_maintainer.wait.github_pr import (
    GitHubPrWaitConfig,
    GitHubPrWaitResult,
    QueryPrChecks,
    query_github_pr_checks,
)
from agent_maintainer.wait.models import WaitRepairCapsule, render_wait_capsule
from agent_maintainer.wait.registry import (
    WAIT_STATUS_PENDING,
    WaitRecord,
    WaitRegistry,
    observe_github_pr,
    wait_records,
)

SWEEP_RUN_ID = "wait-sweep"
Sleep = Callable[[int], None]


@dataclass(frozen=True)
class SweepSummary:
    """Summary of one wait registry sweep."""

    checked: int
    updated: int
    pending: int
    ready: int


@dataclass(frozen=True)
class DetachedWatcher:
    """Detached watcher process metadata."""

    command: tuple[str, ...]


def sweep_once(
    registry: WaitRegistry,
    *,
    query_checks: QueryPrChecks | None = None,
    now: datetime | None = None,
) -> SweepSummary:
    """Poll each pending wait once without printing pending chatter."""

    checked = 0
    updated = 0
    for record in _pending_records(registry):
        checked += 1
        before = registry.read(record.wait_id)
        after = sweep_record(registry, before, query_checks=query_checks, now=now)
        if after != before:
            updated += 1
    records = wait_records(registry)
    return SweepSummary(
        checked=checked,
        updated=updated,
        pending=sum(1 for item in records if item.status == WAIT_STATUS_PENDING),
        ready=sum(1 for item in records if item.ready),
    )


def sweep_record(
    registry: WaitRegistry,
    record: WaitRecord,
    *,
    query_checks: QueryPrChecks | None = None,
    now: datetime | None = None,
) -> WaitRecord:
    """Poll one wait record once and persist meaningful state changes."""

    if record.status != WAIT_STATUS_PENDING:
        return record
    query = query_checks or query_github_pr_checks
    try:
        state = query(_github_pr_config(record))
    except RuntimeError as exc:
        return registry.complete_github_pr(
            record,
            GitHubPrWaitResult(pr_number=record.pr_number, state=None, error=str(exc)),
            now=now,
        )
    if state.completed:
        return registry.complete_github_pr(
            record,
            GitHubPrWaitResult(pr_number=record.pr_number, state=state),
            now=now,
        )
    observed = observe_github_pr(registry, record, state, now=now)
    if _timed_out(observed, now):
        return registry.complete_github_pr(
            observed,
            GitHubPrWaitResult(
                pr_number=observed.pr_number,
                state=state,
                timed_out=True,
            ),
            now=now,
        )
    return observed


def watch_wait(
    registry: WaitRegistry,
    wait_id: str,
    *,
    query_checks: QueryPrChecks | None = None,
    sleep: Sleep = time.sleep,
    now: datetime | None = None,
) -> WaitRecord:
    """Watch one wait until a terminal resume record is ready."""

    while True:
        record = registry.read(wait_id)
        if record.ready:
            return record
        updated = sweep_record(registry, record, query_checks=query_checks, now=now)
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
    # Detached watcher must outlive this command; a context manager would wait.
    subprocess.Popen(  # nosec B603  # pylint: disable=consider-using-with
        list(command),
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return DetachedWatcher(command=command)


def render_sweep_text(summary: SweepSummary) -> str:
    """Render compact one-shot sweep output."""

    return render_wait_capsule(
        WaitRepairCapsule(
            result="PASS",
            run_id=SWEEP_RUN_ID,
            details=(
                f"checked: {summary.checked}",
                f"updated: {summary.updated}",
                f"pending: {summary.pending}",
                f"ready: {summary.ready}",
            ),
        ),
    )


def render_sweep_json(summary: SweepSummary) -> str:
    """Render one sweep summary as JSON."""

    return json.dumps(
        {
            "checked": summary.checked,
            "updated": summary.updated,
            "pending": summary.pending,
            "ready": summary.ready,
        },
        indent=2,
        sort_keys=True,
    )


def _github_pr_config(record: WaitRecord) -> GitHubPrWaitConfig:
    return GitHubPrWaitConfig(
        pr_number=record.pr_number,
        repo=record.repo,
        interval_seconds=record.interval_seconds,
        timeout_seconds=record.timeout_seconds,
    )


def _pending_records(registry: WaitRegistry) -> tuple[WaitRecord, ...]:
    return tuple(item for item in wait_records(registry) if item.status == WAIT_STATUS_PENDING)


def _timed_out(record: WaitRecord, now: datetime | None) -> bool:
    deadline = datetime.fromisoformat(record.deadline_at.replace("Z", "+00:00"))
    current = now or datetime.now(UTC)
    return current.astimezone(UTC) >= deadline
