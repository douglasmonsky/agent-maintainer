"""Build deterministic non-mutating repair plans."""

from __future__ import annotations

import shlex

from agent_maintainer.repair_plan.models import RepairPlan, RepairPlanRequest


def build_repair_plan(request: RepairPlanRequest) -> RepairPlan:
    """Return a deterministic repair plan for selected focus."""
    if request.ratchet:
        return ratchet_plan(request)
    if request.check:
        return check_plan(request, request.check)
    if request.target:
        return target_plan(request, request.target)
    return default_plan(request)


def default_plan(request: RepairPlanRequest) -> RepairPlan:
    """Return general latest-failure repair plan."""
    return RepairPlan(
        mode="default",
        objective="Repair the latest verifier failure with the smallest coherent change.",
        current_target="Latest verifier failure or next ratchet target.",
        recommended_sequence=(
            "Read the latest bounded failure context.",
            "Choose one repair target before editing.",
            "Expand only the file, diff, or log context needed for that target.",
            "Make the smallest code or test change that directly addresses the target.",
            "Run focused tests first, then the precommit profile.",
        ),
        context_commands=common_context_commands(request),
        test_commands=common_test_commands(),
        verification_commands=common_verification_commands(),
        stop_conditions=common_stop_conditions(),
    )


def ratchet_plan(request: RepairPlanRequest) -> RepairPlan:
    """Return plan for repairing one ratchet target."""
    return RepairPlan(
        mode="ratchet",
        objective="Repair one ratchet target without mixing unrelated cleanup.",
        current_target="Top unresolved ratchet target.",
        recommended_sequence=(
            "List current ratchet targets and select one.",
            "Prefer a target already touched by the current diff.",
            "Use bounded file and diff context for the selected target.",
            "Repair the finding instead of lowering thresholds or adding broad suppressions.",
            "Re-run ratchet status and the precommit profile.",
        ),
        context_commands=(
            "python -m agent_maintainer ratchet next --limit 5",
            "python -m agent_maintainer ratchet next --format json",
            *common_context_commands(request),
        ),
        test_commands=common_test_commands(),
        verification_commands=(
            "python -m agent_maintainer ratchet status",
            *common_verification_commands(),
        ),
        stop_conditions=common_stop_conditions(),
    )


def check_plan(request: RepairPlanRequest, check: str) -> RepairPlan:
    """Return plan focused on one verifier check."""
    safe_check = shlex.quote(check)
    return RepairPlan(
        mode="check",
        objective=f"Repair the failing {check} check without broadening suppressions.",
        current_target=f"Verifier check: {check}",
        recommended_sequence=(
            f"Read the bounded {check} log before editing.",
            "Identify the first actionable failure and its owning file.",
            "Expand file or diff context only for that failure.",
            "Fix the root cause or add a narrow test-backed exception if justified.",
            f"Re-run the focused {check} command through Agent Maintainer feedback.",
        ),
        context_commands=(
            f"python -m agent_maintainer context log {safe_check} --tail 120",
            *common_context_commands(request),
        ),
        test_commands=common_test_commands(),
        verification_commands=common_verification_commands(),
        stop_conditions=common_stop_conditions(),
    )


def target_plan(request: RepairPlanRequest, target: str) -> RepairPlan:
    """Return plan focused on one source path."""
    safe_target = shlex.quote(target)
    return RepairPlan(
        mode="target",
        objective="Repair the selected file while keeping the change reviewable.",
        current_target=f"Path: {target}",
        recommended_sequence=(
            "Read the target outline before opening full source.",
            "Review only the target's current diff hunks.",
            "Identify the nearest likely tests before editing.",
            "Keep the fix local unless the context proves a boundary change is required.",
            "Run focused tests and the precommit profile.",
        ),
        context_commands=(
            f"python -m agent_maintainer context file {safe_target} --outline",
            f"python -m agent_maintainer context diff --path {safe_target} --hunks 5",
            *common_context_commands(request),
        ),
        test_commands=common_test_commands(),
        verification_commands=common_verification_commands(),
        stop_conditions=common_stop_conditions(),
    )


def common_context_commands(request: RepairPlanRequest) -> tuple[str, ...]:
    """Return bounded context commands useful for every repair."""
    return (
        "python -m agent_maintainer context failures --limit 20",
        f"python -m agent_maintainer context pack --budget {request.pack_budget}",
    )


def common_test_commands() -> tuple[str, ...]:
    """Return stable test discovery commands."""
    return (
        "python -m agent_maintainer test-intel changed",
        "python -m pytest",
    )


def common_verification_commands() -> tuple[str, ...]:
    """Return standard verification commands for repair completion."""
    return (
        "python -m agent_maintainer verify --profile precommit",
        "python -m agent_maintainer verify --profile full",
    )


def common_stop_conditions() -> tuple[str, ...]:
    """Return conditions that should stop an autonomous repair loop."""
    return (
        "Stop if the repair requires unrelated files or a broader change plan.",
        "Stop if the failing check changes category after the fix.",
        "Stop before lowering thresholds, disabling checks, or adding broad suppressions.",
        "Stop if needed context cannot be bounded safely.",
    )
