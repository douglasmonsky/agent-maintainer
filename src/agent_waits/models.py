"""Shared wait-result output primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

TIMEOUT_EXIT_CODE: Final = 124


def _empty_text() -> tuple[str, ...]:
    return ()


@dataclass(frozen=True)
class WaitRepairCapsule:
    """Compact final status for long-running work."""

    result: str
    run_id: str
    profile: str = ""
    details: tuple[str, ...] = field(default_factory=_empty_text)
    top_repair_facts: tuple[str, ...] = field(default_factory=_empty_text)
    likely_next_action: str = ""
    expand_command: str = ""


def render_wait_capsule(capsule: WaitRepairCapsule) -> str:
    """Render a wait repair capsule without raw logs."""

    lines = [f"Result: {capsule.result}"]
    if capsule.profile:
        lines.append(f"Profile: {capsule.profile}")
    lines.append(f"Run ID: {capsule.run_id}")
    lines.extend(capsule.details)
    if capsule.top_repair_facts:
        lines.extend(("", "Top repair facts:"))
        lines.extend(_numbered(capsule.top_repair_facts))
    if capsule.likely_next_action:
        lines.extend(("", "Likely next action:", capsule.likely_next_action))
    if capsule.expand_command:
        lines.extend(("", "Expand only if needed:", capsule.expand_command))
    return "\n".join(lines)


def _numbered(items: tuple[str, ...]) -> list[str]:
    return [f"{index}. {item}" for index, item in enumerate(items, start=1)]
