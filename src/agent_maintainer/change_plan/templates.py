"""Templates for cohesive change plans."""

from __future__ import annotations

from datetime import date, timedelta

from agent_maintainer.change_plan.models import REQUIRED_SECTIONS

DEFAULT_EXPIRY_DAYS = 14


def render_plan_template(
    slug: str,
    *,
    kind: str = "mechanical-migration",
    base_ref: str = "origin/main",
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
