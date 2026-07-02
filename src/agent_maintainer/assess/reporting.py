"""Text and JSON renderers for assessment reports."""

from __future__ import annotations

import json
from typing import cast

from agent_maintainer.assess.debt_score import (
    category_interpretation,
    score_interpretation,
)
from agent_maintainer.assess.models import (
    DebtScoreReport,
    ReviewabilityCount,
    ReviewabilityReport,
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
        f"Interpretation: {score_interpretation(report.score)}",
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


def render_reviewability_text(report: ReviewabilityReport) -> str:
    """Render advisory provider-aware reviewability summary."""
    lines = [
        "Reviewability Assessment",
        f"Target: {report.target}",
        f"Base ref: {report.base_ref}",
        f"Staged: {report.staged}",
        report.advisory_note,
        "",
        "Summary:",
        f"- Changed files: {report.total_changed_files}",
        f"- Classified provider files: {report.classified_files}",
        f"- Unclassified files: {report.unclassified_files}",
        "",
        "By ecosystem:",
        *_count_lines(report.by_ecosystem),
        "",
        "By role:",
        *_count_lines(report.by_role),
        "",
        "Next commands:",
        *[f"- `{command}`" for command in report.next_commands],
    ]
    if report.changes:
        lines.extend(("", "Changed provider files:"))
        lines.extend(
            (
                f"- {change.path}: {change.ecosystem}/{change.role} "
                f"(+{change.added}/-{change.deleted})"
            )
            for change in report.changes
        )
    return "\n".join(lines)


def _count_lines(counts: tuple[ReviewabilityCount, ...]) -> list[str]:
    """Render deterministic grouping counts."""
    if not counts:
        return ["- None"]
    return [f"- {item.key}: {item.count}" for item in counts]


def render_json(report: object) -> str:
    """Render report as stable JSON."""
    if isinstance(report, DebtScoreReport):
        return json.dumps(debt_to_dict(report), indent=2, sort_keys=True)
    return json.dumps(model_to_dict(report), indent=2, sort_keys=True)


def debt_to_dict(report: DebtScoreReport) -> dict[str, object]:
    """Return debt report JSON with advisory interpretation fields."""
    payload = cast("dict[str, object]", model_to_dict(report))
    payload["interpretation"] = score_interpretation(report.score)
    payload["categories"] = [
        {
            "name": category.name,
            "score": category.score,
            "weight": category.weight,
            "status": category.status,
            "interpretation": category_interpretation(category),
            "evidence": list(category.evidence),
            "recommendations": list(category.recommendations),
        }
        for category in report.categories
    ]
    return payload
