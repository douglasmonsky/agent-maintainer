"""Repair plan data contracts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RepairPlanRequest:
    """Inputs used to produce one bounded repair plan."""

    ratchet: bool = False
    check: str | None = None
    target: str | None = None
    pack_budget: int = 24_000


@dataclass(frozen=True)
class RepairPlan:
    """Agent-facing sequence for repairing one current target."""

    mode: str
    objective: str
    current_target: str
    recommended_sequence: tuple[str, ...]
    context_commands: tuple[str, ...]
    test_commands: tuple[str, ...]
    verification_commands: tuple[str, ...]
    stop_conditions: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return stable JSON-serializable repair plan payload."""
        return {
            "mode": self.mode,
            "non_mutating": True,
            "objective": self.objective,
            "current_target": self.current_target,
            "recommended_sequence": list(self.recommended_sequence),
            "context_commands": list(self.context_commands),
            "test_commands": list(self.test_commands),
            "verification_commands": list(self.verification_commands),
            "stop_conditions": list(self.stop_conditions),
        }
