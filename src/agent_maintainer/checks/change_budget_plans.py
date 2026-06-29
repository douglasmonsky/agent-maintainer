"""Cohesive change-plan support for the change-budget check."""

from __future__ import annotations

import subprocess  # nosec B404
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from agent_maintainer.change_plan import git_scope as change_plan_scope
from agent_maintainer.change_plan import parser as change_plan_parser
from agent_maintainer.change_plan import validation as change_plan_validation
from agent_maintainer.change_plan.models import (
    ACTIVE_STATUS,
    PLAN_DIR,
    ChangedPath,
    ChangePlan,
    ValidationIssue,
)


class FileChangeLike(Protocol):
    """Change-budget file change shape used by plan integration."""

    @property
    def path(self) -> str:
        """Changed path."""
        raise NotImplementedError

    @property
    def added(self) -> int:
        """Added lines."""
        raise NotImplementedError

    @property
    def deleted(self) -> int:
        """Deleted lines."""
        raise NotImplementedError


@dataclass(frozen=True)
class ChangePlanDecision:
    """Evaluated cohesive change plan for current diff."""

    plan: ChangePlan | None = None
    issues: tuple[ValidationIssue, ...] = ()
    changes: tuple[ChangedPath, ...] = ()

    @property
    def allowed(self) -> bool:
        """Return whether plan can bend normal change-budget limits."""

        return self.plan is not None and not self.issues


@dataclass(frozen=True)
class BudgetContext:
    """Repository context for optional change-budget integrations."""

    repo_root: Path | None = None
    all_changes: tuple[FileChangeLike, ...] = ()
    branch_name: str = ""


def evaluate_change_plan(context: BudgetContext | None) -> ChangePlanDecision:
    """Return active change-plan decision for current diff."""

    if context is None or context.repo_root is None or not context.all_changes:
        return ChangePlanDecision()
    plans, parse_issues = load_change_plans(context.repo_root / PLAN_DIR)
    active_plans = [plan for plan in plans if plan.metadata.status == ACTIVE_STATUS]
    if not active_plans:
        return ChangePlanDecision(issues=tuple(parse_issues))
    plan_changes = to_plan_changes(context.all_changes)
    plan = active_plans[0]
    issues = [
        *parse_issues,
        *change_plan_validation.validate_plan(plan),
        *change_plan_scope.scope_issues(plan, plan_changes),
        *change_plan_validation.branch_state_issues(
            plan, context.branch_name or current_branch_name(context)
        ),
    ]
    if len(active_plans) > 1:
        issues.append(
            ValidationIssue(
                path=PLAN_DIR.as_posix(),
                message="only one active change plan may bend change-budget limits",
            )
        )
    return ChangePlanDecision(plan=plan, issues=tuple(issues), changes=plan_changes)


def current_branch_name(context: BudgetContext) -> str:
    """Return current Git branch name for plan validation."""

    if context.repo_root is None:
        return ""
    try:
        return change_plan_scope.current_branch(context.repo_root)
    except (OSError, subprocess.CalledProcessError):
        return ""


def load_change_plans(plan_dir: Path) -> tuple[list[ChangePlan], list[ValidationIssue]]:
    """Load change plans without importing the CLI adapter."""

    plans: list[ChangePlan] = []
    issues: list[ValidationIssue] = []
    for path in sorted(plan_dir.glob("*.md")):
        try:
            plans.append(change_plan_parser.parse_plan(path))
        except change_plan_parser.PlanParseError as exc:
            issues.append(ValidationIssue(path=path.as_posix(), message=str(exc)))
    return plans, issues


def to_plan_changes(changes: tuple[FileChangeLike, ...]) -> tuple[ChangedPath, ...]:
    """Convert change-budget changes to change-plan scope changes."""

    return tuple(
        ChangedPath(path=change.path, added=change.added, deleted=change.deleted)
        for change in changes
    )


def change_plan_failures(decision: ChangePlanDecision) -> list[str]:
    """Return failure messages for invalid active change plan."""

    return [f"Change plan invalid: {issue.path}: {issue.message}" for issue in decision.issues]


def change_plan_messages(decision: ChangePlanDecision) -> list[str]:
    """Return active change-plan informational warning lines."""

    plan = decision.plan
    if plan is None:
        return []
    changed_files = len(decision.changes)
    changed_lines = sum(change.changed_lines for change in decision.changes)
    metadata = plan.metadata
    return [
        (
            f"CHANGE PLAN ACTIVE: {metadata.id}; changed files "
            f"{changed_files}/{metadata.max_changed_files}; changed lines "
            f"{changed_lines}/{metadata.max_changed_lines}. Normal change budget bent; "
            "all other checks still apply."
        )
    ]
