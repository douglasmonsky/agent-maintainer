"""Repo-scoped daemon loop for reliable terminal wait rewake."""

from __future__ import annotations

import os
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from agent_maintainer.runtime_events import waiting as wait_runtime
from agent_maintainer.wait import (
    codex_rewake,
    daemon_launchd,
    daemon_state,
    sweeper,
)
from agent_maintainer.wait import (
    registry as wait_registry,
)
from agent_waits.notifications import (
    DEFAULT_NOTIFICATION_LEASE_SECONDS,
    FAILURE_LEASE_EXPIRED,
    repair_stale_notifications,
)
from agent_waits.watcher_state import mark_pending_watcher_polls

Sleep = Callable[[float], None]
Monotonic = Callable[[], float]

CodexRewakeBackend = codex_rewake.CodexRewakeBackend
codex_rewake_resumed = codex_rewake.codex_rewake_resumed
DAEMON_IDLE_TIMEOUT_SECONDS = daemon_launchd.DAEMON_IDLE_TIMEOUT_SECONDS
DAEMON_INTERVAL_SECONDS = daemon_launchd.DAEMON_INTERVAL_SECONDS


@dataclass(frozen=True)
class DaemonLoopHooks:
    """Injectable daemon loop hooks for tests."""

    sleep: Sleep = time.sleep
    monotonic: Monotonic = time.monotonic
    env: Mapping[str, str] | None = None


def run_daemon(
    root: Path,
    *,
    interval_seconds: int = DAEMON_INTERVAL_SECONDS,
    idle_timeout_seconds: int = DAEMON_IDLE_TIMEOUT_SECONDS,
    hooks: DaemonLoopHooks | None = None,
) -> int:
    """Run daemon loop until idle timeout expires."""

    registry = wait_registry.WaitRegistry(root)
    active_hooks = DaemonLoopHooks() if hooks is None else hooks
    started = active_hooks.monotonic()
    last_activity = started
    current = os.environ if active_hooks.env is None else active_hooks.env
    while active_hooks.monotonic() - last_activity < idle_timeout_seconds:
        summary = sweeper.sweep_once(registry)
        mark_pending_watcher_polls(registry)
        _emit_stale_notification_failures(
            repair_stale_notifications(
                registry,
                lease_seconds=DEFAULT_NOTIFICATION_LEASE_SECONDS,
            ),
        )
        resumed = _resume_ready_with_envelopes(registry, root, current)
        records = wait_registry.wait_records(registry)
        if summary.updated or resumed or _has_active_work(root, records):
            last_activity = active_hooks.monotonic()
        daemon_state.write_heartbeat(root, summary_checked=summary.checked, resumed=resumed)
        active_hooks.sleep(interval_seconds)
    return 0


def _resume_ready_with_envelopes(
    registry: wait_registry.WaitRegistry,
    root: Path,
    env: Mapping[str, str],
) -> int:
    resumed = 0
    for record in wait_registry.wait_records(registry):
        if record.status != wait_registry.WAIT_STATUS_READY:
            continue
        envelope = daemon_state.read_rewake_envelope(root, record.wait_id)
        if envelope is None:
            continue
        merged_env = {**env, **envelope}
        result = CodexRewakeBackend(registry, env=merged_env).resume_if_available(record)
        persisted = registry.read(record.wait_id)
        if codex_rewake_resumed(result) and persisted.status == wait_registry.WAIT_STATUS_RESUMED:
            wait_runtime.WaitRuntimeEvents.create(
                target_kind=persisted.kind,
                target_id=persisted.target_id,
            ).resumed(wait_id=persisted.wait_id)
            resumed += 1
    return resumed


def _has_active_work(
    root: Path,
    records: tuple[wait_registry.WaitRecord, ...],
) -> bool:
    return any(
        record.status == wait_registry.WAIT_STATUS_PENDING
        or daemon_state.has_rewake_envelope(root, record.wait_id)
        for record in records
    )


def _emit_stale_notification_failures(
    records: tuple[wait_registry.WaitRecord, ...],
) -> None:
    for record in records:
        events = wait_runtime.WaitRuntimeEvents.create(
            target_kind=record.kind,
            target_id=record.target_id,
        )
        wait_runtime.emit_notify_failed(
            events,
            wait_id=record.wait_id,
            reason=FAILURE_LEASE_EXPIRED,
        )
