"""Text and JSON renderers for assessment reports."""

from __future__ import annotations

import json

from agent_maintainer.assess.models import (
    DebtScoreReport,
    SetupAdvisorReport,
)
from agent_maintainer.assess.models import (
    to_dict as model_to_dict,
)


def render_setup_text(report: SetupAdvisorReport) -> str:
    """Render setup advisor report for humans and agents."""
    lines = [
        "Setup Advisor",
        f"Target: {report.target}",
        f"Recommended track: {report.track}",
        f"Recommended preset: {report.preset}",
        f"Confidence: {report.confidence}",
        "",
        "Why:",
        *[f"- {reason}" for reason in report.reasons],
        "",
        "Optional gates:",
    ]
    if report.optional_gates:
        lines.extend(
            f"- {gate.name}: {gate.recommendation} ({gate.config_key}) - {gate.reason}"
            for gate in report.optional_gates
        )
    else:
        lines.append("- No optional gates recommended from current evidence.")
    lines.extend(("", "Agent follow-up prompts:"))
    lines.extend(f"- {prompt}" for prompt in report.agent_prompts)
    lines.extend(("", "Next commands:"))
    lines.extend(f"- `{command}`" for command in report.next_commands)
    return "\n".join(lines)


def render_debt_text(report: DebtScoreReport) -> str:
    """Render Technical Debt Score for humans and agents."""
    lines = [
        "Technical Debt Score",
        f"Target: {report.target}",
        f"Score: {report.score}/100 ({report.risk})",
        f"Confidence: {report.confidence}",
        report.summary,
        "",
        "Categories:",
    ]
    lines.extend(
        f"- {category.name}: {category.score}/100 ({category.status})"
        for category in report.categories
    )
    lines.extend(("", "Next actions:"))
    lines.extend(f"- {action}" for action in report.next_actions)
    lines.extend(("", "Artifacts:"))
    lines.extend(f"- {path}" for path in report.artifact_paths)
    return "\n".join(lines)


def render_json(report: object) -> str:
    """Render report as stable JSON."""
    return json.dumps(model_to_dict(report), indent=2, sort_keys=True)
