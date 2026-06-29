"""Validate cohesive change plans."""

from __future__ import annotations

from datetime import date

from agent_maintainer.change_plan.models import (
    ACTIVE_STATUS,
    REQUIRED_SECTIONS,
    ChangePlan,
    ValidationIssue,
)
from agent_maintainer.change_plan.parser import normalized_heading

MIN_SECTION_LENGTH = 12


def validate_plan(plan: ChangePlan, *, today: date | None = None) -> tuple[ValidationIssue, ...]:
    """Return validation issues for one cohesive change plan."""

    current_date = today or date.today()
    issues: list[ValidationIssue] = []
    issues.extend(metadata_issues(plan, current_date))
    issues.extend(section_issues(plan))
    return tuple(issues)


def metadata_issues(plan: ChangePlan, today: date) -> tuple[ValidationIssue, ...]:
    """Return metadata validation issues."""

    metadata = plan.metadata
    issues: list[ValidationIssue] = []
    if metadata.status != ACTIVE_STATUS:
        issues.append(issue(plan, f"status must be {ACTIVE_STATUS!r}"))
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
    return tuple(issues)


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
