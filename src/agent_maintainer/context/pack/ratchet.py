"""Ratchet state helpers for context packs."""

from __future__ import annotations

from pathlib import Path

from agent_maintainer.core.structured_values import json_array, json_object
from agent_maintainer.ratchet.baseline import read_baseline
from agent_maintainer.ratchet.ranking import changed_paths, ranked_targets
from agent_maintainer.ratchet.status import status_report


def ratchet_payload(
    *,
    baseline_path: Path | None,
    base_ref: str,
    target_limit: int,
    live_recompute: bool = True,
) -> dict[str, object]:
    """Return ratchet state targets when a baseline exists."""

    if not live_recompute:
        return _unavailable_payload(
            baseline_path,
            reason="live ratchet recomputation disabled for this bounded context request",
        )
    if baseline_path is None or not baseline_path.exists():
        return _unavailable_payload(baseline_path, reason="ratchet baseline not found")

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

    targets = json_array(ratchet_state.get("top_targets"))
    if targets is None:
        return ()
    commands = (_target_command(target) for target in targets)
    return tuple(command for command in commands if command is not None)


def _unavailable_payload(
    baseline_path: Path | None,
    *,
    reason: str,
) -> dict[str, object]:
    """Return the stable payload shape for unavailable ratchet state."""

    return {
        "baseline_path": None if baseline_path is None else str(baseline_path),
        "available": False,
        "reason": reason,
        "counts": {},
        "stale_reasons": [],
        "top_targets": [],
    }


def _target_command(target: object) -> str | None:
    """Return one target command when the payload item is valid."""

    payload = json_object(target)
    if payload is None or not payload.get("first_command"):
        return None
    return str(payload["first_command"])
