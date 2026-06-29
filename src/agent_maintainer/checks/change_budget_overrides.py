"""Apply legacy change-budget override policies."""

from __future__ import annotations

from collections.abc import Sequence

from agent_maintainer.checks import cohesive_override
from agent_maintainer.core.config import MaintainerConfig

CHANGE_PLAN_FAILURE_PREFIX = "Change plan invalid:"


def has_change_plan_failures(failures: list[str]) -> bool:
    """Return whether failures include authoritative change-plan failures."""
    return any(failure.startswith(CHANGE_PLAN_FAILURE_PREFIX) for failure in failures)


def apply_cohesive_override(
    failures: list[str],
    warnings: list[str],
    config: MaintainerConfig,
    py_source_changes: Sequence[cohesive_override.FileChangeLike],
) -> tuple[list[str], list[str]]:
    """Apply legacy override without clearing change-plan failures."""
    if not failures:
        return failures, warnings

    override_decision = cohesive_override.evaluate_override(config, py_source_changes)
    if override_decision.allowed and not has_change_plan_failures(failures):
        return [], [*warnings, *override_decision.warnings]
    if override_decision.allowed:
        return failures, [
            *warnings,
            "Cohesive-change override ignored because active change-plan validation failed.",
        ]
    if override_decision.requested:
        return [*failures, *override_decision.failures], warnings
    return failures, warnings
