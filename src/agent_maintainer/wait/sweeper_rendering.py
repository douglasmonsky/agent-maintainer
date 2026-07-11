"""Rendering helpers for wait sweeper summaries."""

from __future__ import annotations

import json
from typing import Final

from agent_maintainer.wait import daemon_launchd
from agent_maintainer.wait.sweeper import CleanupSummary, SweepSummary
from agent_waits.models import WaitRepairCapsule, render_wait_capsule

SWEEP_RUN_ID: Final = "wait-sweep"


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
    """Render one sweep summary JSON."""

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


def render_sweep(summary: SweepSummary, *, as_json: bool) -> str:
    """Render one sweep summary in the requested stable format."""

    if as_json:
        return render_sweep_json(summary)
    return render_sweep_text(summary)


def render_cleanup(summary: CleanupSummary, *, as_json: bool) -> str:
    """Render one cleanup summary in the requested stable format."""

    if as_json:
        return f'{{"expired_ready": {summary.expired_ready}}}'
    return f"expired ready waits: {summary.expired_ready}"


def render_daemon_launch(
    result: daemon_launchd.DaemonLaunch,
    *,
    as_json: bool,
) -> str:
    """Render one daemon installation result."""

    if as_json:
        return json.dumps(
            {
                "started": result.started,
                "label": result.label,
                "log_path": str(result.log_path),
                "error": result.error,
            },
            sort_keys=True,
        )
    if result.started:
        return f"daemon installed: {result.label}\nlog: {result.log_path}"
    return f"daemon not started: {result.error}"


def render_daemon_status(
    status: daemon_launchd.DaemonStatus,
    *,
    as_json: bool,
) -> str:
    """Render one daemon status result."""

    if as_json:
        return json.dumps(
            {
                "label": status.label,
                "plist_path": str(status.plist_path),
                "log_path": str(status.log_path),
                "loaded": status.loaded,
                "pid": status.pid,
                "last_heartbeat": status.last_heartbeat,
                "error": status.error,
            },
            indent=2,
            sort_keys=True,
        )
    return daemon_launchd.status_text(status)
