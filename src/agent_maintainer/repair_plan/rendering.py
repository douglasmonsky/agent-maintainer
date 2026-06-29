"""Render repair plans for agents and automation."""

from __future__ import annotations

import json

from agent_maintainer.context.budget import bound_text
from agent_maintainer.context.models import ContextBudget
from agent_maintainer.repair_plan.models import RepairPlan


def render_markdown(plan: RepairPlan, *, budget: int) -> str:
    """Return bounded Markdown repair plan."""
    sections = (
        ("objective", (plan.objective,)),
        ("current target", (plan.current_target,)),
        ("recommended sequence", plan.recommended_sequence),
        ("context commands", plan.context_commands),
        ("test commands", plan.test_commands),
        ("verification commands", plan.verification_commands),
        ("stop conditions", plan.stop_conditions),
    )
    lines = ["# Repair Plan", ""]
    for heading, values in sections:
        lines.extend(render_section(heading, values))
    body = "\n".join(lines).rstrip()
    rendered = f"{body}\n"
    return bound_text(rendered, ContextBudget(max_chars=budget, max_items=1)).text


def render_json(plan: RepairPlan, *, budget: int) -> str:
    """Return bounded JSON repair plan."""
    body = json.dumps(plan.to_dict(), indent=2, sort_keys=True)
    rendered = f"{body}\n"
    return bound_text(rendered, ContextBudget(max_chars=budget, max_items=1)).text


def render_section(heading: str, values: tuple[str, ...]) -> list[str]:
    """Return Markdown lines for one repair plan section."""
    lines = [f"## {heading}"]
    if len(values) == 1:
        lines.append(values[0])
    else:
        lines.extend(
            f"- `{value}`" if value.startswith("python ") else f"- {value}" for value in values
        )
    lines.append("")
    return lines
