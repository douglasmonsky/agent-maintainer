"""Ratchet state helpers for context packs."""

from __future__ import annotations

from pathlib import Path

from agent_maintainer.ratchet.baseline import read_baseline
from agent_maintainer.ratchet.ranking import changed_paths, ranked_targets
from agent_maintainer.ratchet.status import status_report


def ratchet_payload(
    *,
    baseline_path: Path | None,
    base_ref: str,
    target_limit: int,
) -> dict[str, object]:
    """Return ratchet state targets when a baseline exists."""

    if baseline_path is None or not baseline_path.exists():
        return {
            "baseline_path": None if baseline_path is None else str(baseline_path),
            "available": False,
            "reason": "ratchet baseline not found",
            "counts": {},
            "stale_reasons": [],
            "top_targets": [],
        }

    baseline = read_baseline(baseline_path)
    report = status_report(baseline, base_ref=base_ref)
    targets = ranked_targets(
        report,
        changed_path_set=changed_paths(base_ref),
        limit=target_limit,
    )
    return {
        "baseline_path": str(baseline_path),
        "available": True,
        "counts": report.counts(),
        "stale_reasons": list(report.stale_reasons),
        "top_targets": [target.to_dict() for target in targets],
    }


def target_commands(ratchet_state: dict[str, object]) -> tuple[str, ...]:
    """Return first expansion commands from ratchet target payload."""

    targets = ratchet_state.get("top_targets", [])
    if not isinstance(targets, list):
        return ()
    return tuple(
        str(target["first_command"])
        for target in targets
        if isinstance(target, dict) and target.get("first_command")
    )
