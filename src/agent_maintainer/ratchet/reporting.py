"""Render ratchet target reports."""

from __future__ import annotations

import json

from agent_maintainer.ratchet.ranking import RatchetTarget


def render_targets_text(targets: tuple[RatchetTarget, ...]) -> str:
    """Return compact text for ranked targets."""

    if not targets:
        return "No ratchet targets found."
    lines = ["Top ratchet targets:"]
    for target in targets:
        lines.extend(target_lines(target))
    return "\n".join(lines)


def render_targets_json(targets: tuple[RatchetTarget, ...]) -> str:
    """Return JSON for ranked targets."""

    payload = {"targets": [target.to_dict() for target in targets]}
    return json.dumps(payload, indent=2, sort_keys=True)


def target_lines(target: RatchetTarget) -> tuple[str, ...]:
    """Return text lines for one target."""

    return (
        f"{target.rank}. {target.path}",
        f"   Why target: {target.why}",
        f"   Current: {target.current}",
        f"   First command: {target.first_command}",
    )
