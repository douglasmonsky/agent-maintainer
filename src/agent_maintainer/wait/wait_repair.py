"""Explicit stale watcher repair for durable pending waits."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final

from agent_maintainer.runtime_events.waiting import WaitRuntimeEvents
from agent_maintainer.wait import broker, daemon_launchd
from agent_maintainer.wait.registry import WaitRecord, WaitRegistry, wait_records
from agent_waits.notifications import (
    FAILURE_LEASE_EXPIRED,
    claim_watcher_started_observation,
    repair_stale_notifications,
)
from agent_waits.watcher_state import (
    WatcherState,
    claim_watcher_repair,
    mark_watcher_failed,
    mark_watcher_started,
    watcher_repair_eligible,
    watcher_state,
)

DEFAULT_STALE_AFTER_SECONDS: Final = 60
WatcherActive = Callable[[Path, WatcherState], bool]
WatcherStarter = Callable[[Path, WaitRecord], broker.BackgroundWaitRegistration]


@dataclass(frozen=True)
class RepairRequest:
    """Inputs for one bounded watcher repair pass."""

    wait_id: str | None = None
    stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS
    dry_run: bool = False
    now: datetime | None = None


@dataclass(frozen=True)
class RepairHooks:
    """Injectable watcher dependencies for deterministic repair tests."""

    watcher_active: WatcherActive | None = None
    starter: WatcherStarter = broker.start_registered_watcher


@dataclass(frozen=True)
class RepairSummary:
    """Compact result from one watcher repair pass."""

    checked: int
    eligible: int
    repaired: int
    skipped: int
    failed: int
    dry_run: bool
    notification_failures: int = 0

    @property
    def exit_code(self) -> int:
        """Return nonzero only when an attempted repair failed."""

        return 1 if self.failed else 0

    def as_dict(self) -> dict[str, object]:
        """Return stable machine-readable repair output."""

        return {
            "checked": self.checked,
            "eligible": self.eligible,
            "repaired": self.repaired,
            "skipped": self.skipped,
            "failed": self.failed,
            "dry_run": self.dry_run,
            "notification_failures": self.notification_failures,
            "exit_code": self.exit_code,
        }


@dataclass(frozen=True)
class _RepairOutcome:
    eligible: int = 0
    repaired: int = 0
    skipped: int = 0
    failed: int = 0


@dataclass(frozen=True)
class _RepairContext:
    root: Path
    registry: WaitRegistry
    request: RepairRequest
    active_check: WatcherActive
    starter: WatcherStarter


def repair_waits(
    root: Path,
    *,
    request: RepairRequest | None = None,
    hooks: RepairHooks | None = None,
) -> RepairSummary:
    """Repair stale inactive pending watchers after an atomic per-wait claim."""

    registry = WaitRegistry(root)
    active_request = RepairRequest() if request is None else request
    active_hooks = RepairHooks() if hooks is None else hooks
    records = _selected_records(registry, active_request.wait_id)
    active_check = (
        _watcher_active if active_hooks.watcher_active is None else active_hooks.watcher_active
    )
    context = _RepairContext(
        root=root,
        registry=registry,
        request=active_request,
        active_check=active_check,
        starter=active_hooks.starter,
    )
    outcomes = tuple(_repair_record(context, record) for record in records)
    return RepairSummary(
        checked=len(records),
        eligible=sum(outcome.eligible for outcome in outcomes),
        repaired=sum(outcome.repaired for outcome in outcomes),
        skipped=sum(outcome.skipped for outcome in outcomes),
        failed=sum(outcome.failed for outcome in outcomes),
        dry_run=active_request.dry_run,
        notification_failures=_repair_notification_claims(registry, active_request),
    )


def _repair_record(context: _RepairContext, record: WaitRecord) -> _RepairOutcome:
    active = context.active_check(context.root, watcher_state(record))
    if not watcher_repair_eligible(
        record,
        active=active,
        stale_after_seconds=context.request.stale_after_seconds,
        now=context.request.now,
    ):
        return _RepairOutcome(skipped=1)
    if context.request.dry_run:
        return _RepairOutcome(eligible=1)
    claimed = claim_watcher_repair(
        context.registry,
        record.wait_id,
        active_check=lambda state: context.active_check(context.root, state),
        stale_after_seconds=context.request.stale_after_seconds,
        now=context.request.now,
    )
    if claimed is None:
        return _RepairOutcome(eligible=1, skipped=1)
    return _start_claimed_watcher(context, claimed)


def _start_claimed_watcher(
    context: _RepairContext,
    claimed: WaitRecord,
) -> _RepairOutcome:
    try:
        registration = context.starter(context.root, claimed)
    except (OSError, RuntimeError, TimeoutError):
        _mark_repair_failed(context, claimed)
        return _RepairOutcome(eligible=1, failed=1)
    if not registration.watcher_started:
        _mark_repair_failed(context, claimed)
        return _RepairOutcome(eligible=1, failed=1)
    started = mark_watcher_started(
        context.registry,
        claimed,
        strategy=registration.watcher_strategy,
        pid=registration.watcher_pid,
        now=context.request.now,
    )
    observed = claim_watcher_started_observation(
        context.registry,
        started.wait_id,
        now=context.request.now,
    )
    if observed is not None:
        _wait_events(observed).watcher_started(
            wait_id=observed.wait_id,
            strategy=watcher_state(observed).strategy,
        )
    return _RepairOutcome(eligible=1, repaired=1)


def _mark_repair_failed(context: _RepairContext, claimed: WaitRecord) -> None:
    failed = mark_watcher_failed(
        context.registry,
        claimed,
        error_code="watcher_repair_failed",
        now=context.request.now,
    )
    _wait_events(failed).watcher_failed(
        wait_id=failed.wait_id,
        reason=watcher_state(failed).error_code,
    )


def _repair_notification_claims(
    registry: WaitRegistry,
    request: RepairRequest,
) -> int:
    if request.dry_run:
        return 0
    failed = repair_stale_notifications(
        registry,
        lease_seconds=request.stale_after_seconds,
        wait_id=request.wait_id,
        now=request.now,
    )
    for record in failed:
        WaitRuntimeEvents.create(
            target_kind=record.kind,
            target_id=record.target_id,
        ).notify_failed(
            wait_id=record.wait_id,
            reason=FAILURE_LEASE_EXPIRED,
        )
    return len(failed)


def _wait_events(record: WaitRecord) -> WaitRuntimeEvents:
    return WaitRuntimeEvents.create(target_kind=record.kind, target_id=record.target_id)


def render_repair_text(summary: RepairSummary) -> str:
    """Render compact repair summary."""

    result = "PASS" if summary.exit_code == 0 else "ERROR"
    return (
        f"Result: {result}\nChecked: {summary.checked}\nEligible: {summary.eligible}\n"
        f"Repaired: {summary.repaired}\nSkipped: {summary.skipped}\nFailed: {summary.failed}\n"
        f"Notification failures: {summary.notification_failures}\n"
        f"Dry run: {str(summary.dry_run).lower()}"
    )


def render_repair_json(summary: RepairSummary) -> str:
    """Render stable JSON repair summary."""

    return json.dumps(summary.as_dict(), sort_keys=True)


def _selected_records(registry: WaitRegistry, wait_id: str | None) -> tuple[WaitRecord, ...]:
    if wait_id is None:
        return wait_records(registry)
    return (registry.read(wait_id),)


def _watcher_active(root: Path, state: WatcherState) -> bool:
    if state.strategy == "popen" and state.pid is not None:
        return _pid_alive(state.pid)
    if state.strategy == "launchd":
        try:
            return daemon_launchd.daemon_status(root).loaded
        except OSError:
            return False
    return False


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (OSError, ValueError):
        return False
    return True
