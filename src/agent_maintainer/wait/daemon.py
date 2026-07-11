"""Repo-scoped daemon loop for reliable terminal wait rewake."""

from __future__ import annotations

import os
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from agent_maintainer.wait.codex_rewake import CodexRewakeBackend, codex_rewake_resumed
from agent_maintainer.wait.daemon_launchd import (
    DAEMON_IDLE_TIMEOUT_SECONDS,
    DAEMON_INTERVAL_SECONDS,
)
from agent_maintainer.wait.daemon_state import (
    has_rewake_envelope,
    read_rewake_envelope,
    write_heartbeat,
)
from agent_maintainer.wait.registry import (
    WAIT_STATUS_PENDING,
    WAIT_STATUS_READY,
    WaitRecord,
    WaitRegistry,
    wait_records,
)
from agent_maintainer.wait.sweeper import sweep_once
from agent_waits.notifications import (
    DEFAULT_NOTIFICATION_LEASE_SECONDS,
    repair_stale_notifications,
)
from agent_waits.watcher_state import mark_pending_watcher_polls

Sleep = Callable[[float], None]
Monotonic = Callable[[], float]


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

    registry = WaitRegistry(root)
    active_hooks = DaemonLoopHooks() if hooks is None else hooks
    started = active_hooks.monotonic()
    last_activity = started
    current = os.environ if active_hooks.env is None else active_hooks.env
    while active_hooks.monotonic() - last_activity < idle_timeout_seconds:
        summary = sweep_once(registry)
        mark_pending_watcher_polls(registry)
        repair_stale_notifications(
            registry,
            lease_seconds=DEFAULT_NOTIFICATION_LEASE_SECONDS,
        )
        resumed = _resume_ready_with_envelopes(registry, root, current)
        records = wait_records(registry)
        if summary.updated or resumed or _has_active_work(root, records):
            last_activity = active_hooks.monotonic()
        write_heartbeat(root, summary_checked=summary.checked, resumed=resumed)
        active_hooks.sleep(interval_seconds)
    return 0


def _resume_ready_with_envelopes(
    registry: WaitRegistry,
    root: Path,
    env: Mapping[str, str],
) -> int:
    resumed = 0
    for record in wait_records(registry):
        if record.status != WAIT_STATUS_READY:
            continue
        envelope = read_rewake_envelope(root, record.wait_id)
        if envelope is None:
            continue
        merged_env = {**env, **envelope}
        result = CodexRewakeBackend(registry, env=merged_env).resume_if_available(record)
        if codex_rewake_resumed(result):
            resumed += 1
    return resumed


def _has_active_work(root: Path, records: tuple[WaitRecord, ...]) -> bool:
    return any(
        record.status == WAIT_STATUS_PENDING or has_rewake_envelope(root, record.wait_id)
        for record in records
    )
