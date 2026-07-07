"""Rendering helpers for wait sweeper summaries."""

from __future__ import annotations

import json
from typing import Final

from agent_maintainer.wait.sweeper import SweepSummary
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
