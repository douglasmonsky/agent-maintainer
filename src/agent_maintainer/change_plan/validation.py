"""Validate cohesive change plans."""

from __future__ import annotations

from datetime import date

from agent_maintainer.change_plan.models import (
    ACTIVE_STATUS,
    REQUIRED_SECTIONS,
    VALID_STATUSES,
    ChangePlan,
    ValidationIssue,
)
from agent_maintainer.change_plan.parser import normalized_heading

MIN_SECTION_LENGTH = 12
INTEGRATION_BRANCH_SERIES = "integration-branch-series"


def validate_plan(plan: ChangePlan, *, today: date | None = None) -> tuple[ValidationIssue, ...]:
    """Return validation issues for one cohesive change plan."""

    current_date = today or date.today()
    issues: list[ValidationIssue] = []
    issues.extend(metadata_issues(plan, current_date))
    if plan.metadata.status in VALID_STATUSES and plan.metadata.status != ACTIVE_STATUS:
        return tuple(issues)
    issues.extend(section_issues(plan))
    return tuple(issues)


def metadata_issues(plan: ChangePlan, today: date) -> tuple[ValidationIssue, ...]:
    """Return metadata validation issues."""

    metadata = plan.metadata
    issues: list[ValidationIssue] = []
    if metadata.status not in VALID_STATUSES:
        choices = ", ".join(repr(status) for status in VALID_STATUSES)
        issues.append(issue(plan, f"status must be one of: {choices}"))
    if metadata.status in VALID_STATUSES and metadata.status != ACTIVE_STATUS:
        return tuple(issues)
    if metadata.expires < today:
        expiry = metadata.expires.isoformat()
        issues.append(issue(plan, f"plan expired on {expiry}"))
    if not metadata.allowed_paths:
        issues.append(issue(plan, "allowed_paths must contain at least one pattern"))
    if metadata.max_changed_files <= 0:
        issues.append(issue(plan, "max_changed_files must be positive"))
    if metadata.max_changed_lines <= 0:
        issues.append(issue(plan, "max_changed_lines must be positive"))
    if metadata.requires_full_verify is False:
        issues.append(issue(plan, "requires_full_verify must be true"))
    if any(not target.endswith(".py") for target in metadata.ratchet_targets):
        issues.append(issue(plan, "ratchet_targets must point to Python files"))
    issues.extend(integration_branch_issues(plan))
    return tuple(issues)


def integration_branch_issues(plan: ChangePlan) -> tuple[ValidationIssue, ...]:
    """Return integration-branch-series metadata issues."""

    metadata = plan.metadata
    if metadata.kind != INTEGRATION_BRANCH_SERIES:
        return ()
    issues: list[ValidationIssue] = []
    for key, value in (
        ("integration_branch", metadata.integration_branch),
        ("target_branch", metadata.target_branch),
        ("merge_strategy", metadata.merge_strategy),
    ):
        if not value:
            issues.append(issue(plan, f"{key} must be set for integration-branch-series"))
        elif has_invalid_branch_field_chars(value):
            issues.append(issue(plan, f"{key} must not contain whitespace or control characters"))
    if not metadata.expected_units:
        issues.append(issue(plan, "expected_units must list planned integration units"))
    return tuple(issues)


def has_invalid_branch_field_chars(value: str) -> bool:
    """Return whether branch-series metadata contains unsafe spacing."""

    return any(character.isspace() for character in value)


def branch_state_issues(plan: ChangePlan, current_branch: str) -> tuple[ValidationIssue, ...]:
    """Return branch-state issues for integration branch series plans."""

    metadata = plan.metadata
    if metadata.kind != INTEGRATION_BRANCH_SERIES:
        return ()
    if not current_branch:
        return (
            issue(
                plan,
                "current branch must be available for integration-branch-series",
            ),
        )
    if current_branch != metadata.integration_branch:
        return (
            issue(
                plan,
                (
                    f"current branch {current_branch!r} does not match "
                    f"integration_branch {metadata.integration_branch!r}"
                ),
            ),
        )
    return ()


def section_issues(plan: ChangePlan) -> tuple[ValidationIssue, ...]:
    """Return required-section validation issues."""

    issues: list[ValidationIssue] = []
    for section in REQUIRED_SECTIONS:
        body = plan.sections.get(normalized_heading(section), "")
        if len(body.strip()) < MIN_SECTION_LENGTH:
            issues.append(issue(plan, f"missing required section: {section}"))
    return tuple(issues)


def issue(plan: ChangePlan, message: str) -> ValidationIssue:
    """Return issue object for a plan."""

    return ValidationIssue(path=plan.path.as_posix(), message=message)
