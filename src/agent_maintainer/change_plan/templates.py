"""Templates for cohesive change plans."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from agent_maintainer.change_plan.models import REQUIRED_SECTIONS

DEFAULT_EXPIRY_DAYS = 14


@dataclass(frozen=True)
class IntegrationBranchTemplate:
    """Template options for integration branch series plans."""

    branch: str = ""
    target_branch: str = "main"
    merge_strategy: str = "squash-after-series"
    expected_units: tuple[str, ...] = ()


def render_plan_template(
    slug: str,
    *,
    kind: str = "mechanical-migration",
    base_ref: str = "origin/main",
    integration_branch: IntegrationBranchTemplate | None = None,
    today: date | None = None,
) -> str:
    """Return starter markdown for a cohesive change plan."""

    current_date = today or date.today()
    expires = current_date + timedelta(days=DEFAULT_EXPIRY_DAYS)
    lines = [
        "+++",
        f'id = "{slug}"',
        f'kind = "{kind}"',
        'status = "active"',
        f'base_ref = "{base_ref}"',
        *integration_branch_lines(
            slug,
            kind=kind,
            integration_branch=integration_branch,
        ),
        f"expires = {expires.isoformat()}",
        'allowed_paths = ["src/**", "tests/**", "docs/**", "pyproject.toml"]',
        'forbidden_paths = ["config/prod/**", ".env", ".env.*"]',
        "max_changed_files = 120",
        "max_changed_lines = 12000",
        "allow_source_without_test_change = false",
        "requires_tests = true",
        "requires_full_verify = true",
        "ratchet_targets = []",
        "+++",
        f"# Cohesive Change Plan: {slug}",
        "",
    ]
    for section in REQUIRED_SECTIONS:
        lines.extend((f"## {section}", "TODO: explain this requirement.", ""))
    rendered = "\n".join(lines).rstrip()
    return f"{rendered}\n"


def integration_branch_lines(
    slug: str,
    *,
    kind: str,
    integration_branch: IntegrationBranchTemplate | None,
) -> list[str]:
    """Return TOML lines for integration branch plans."""

    if kind != "integration-branch-series":
        return []
    options = integration_branch or IntegrationBranchTemplate()
    branch = options.branch or f"ratchet/{slug}"
    units = options.expected_units or ("TODO: first integration unit",)
    lines = [
        f'integration_branch = "{toml_string(branch)}"',
        f'target_branch = "{toml_string(options.target_branch)}"',
        f'merge_strategy = "{toml_string(options.merge_strategy)}"',
        "expected_units = [",
    ]
    lines.extend(f'  "{toml_string(unit)}",' for unit in units)
    lines.append("]")
    return lines


def toml_string(value: str) -> str:
    """Return minimal TOML string escaping for generated templates."""

    return value.replace("\\", r"\\").replace('"', r"\"")
