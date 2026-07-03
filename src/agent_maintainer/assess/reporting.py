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
    FileBaselineFinding,
    FileBaselineReport,
    ReviewabilityCount,
    ReviewabilityFinding,
    ReviewabilityProviderSummary,
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
        f"- Advisory suppressions: {len(report.suppressions)}",
        f"- Broad advisory suppressions: {report.broad_suppressions}",
        "",
        "By ecosystem:",
        *_count_lines(report.by_ecosystem),
        "",
        "By role:",
        *_count_lines(report.by_role),
        "",
        "Provider summaries:",
        *_provider_summary_lines(report.provider_summaries),
        "",
        "Advisory findings:",
        *_finding_lines(report.advisory_findings),
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
    if report.suppressions:
        lines.extend(("", "Advisory suppressions:"))
        lines.extend(
            (f"- {finding.path}: {finding.ecosystem}/{finding.kind} broad={finding.broad}")
            for finding in report.suppressions
        )
    return "\n".join(lines)


def render_file_baselines_text(report: FileBaselineReport) -> str:
    """Render advisory provider-neutral file baseline summary."""
    lines = [
        "File Baseline Assessment",
        f"Target: {report.target}",
        f"Mode: {report.mode}",
        f"Enabled: {report.enabled}",
        "",
        "Groups:",
    ]
    if report.groups:
        lines.extend(
            f"- {group.name} ({group.role}): matched={group.matched_files}, "
            f"changed={group.changed_files} files/{group.changed_lines} lines, "
            f"findings={group.findings}"
            for group in report.groups
        )
    else:
        lines.append("- None")
    lines.extend(("", "Findings:"))
    if report.findings:
        lines.extend(_file_baseline_finding_line(finding) for finding in report.findings)
    else:
        lines.append("- None")
    lines.extend(("", "Next commands:"))
    lines.extend(f"- `{command}`" for command in report.next_commands)
    return "\n".join(lines)


def _file_baseline_finding_line(finding: FileBaselineFinding) -> str:
    """Render one file-baseline finding without complex f-strings."""
    path_prefix = f"{finding.path}: " if finding.path else ""
    return (
        f"- {finding.group}/{finding.kind}: "
        f"{path_prefix}{finding.message}. {finding.recommendation}"
    )


def _count_lines(counts: tuple[ReviewabilityCount, ...]) -> list[str]:
    """Render deterministic grouping counts."""
    if not counts:
        return ["- None"]
    return [f"- {item.key}: {item.count}" for item in counts]


def _provider_summary_lines(
    summaries: tuple[ReviewabilityProviderSummary, ...],
) -> list[str]:
    """Render advisory provider summary lines."""
    if not summaries:
        return ["- None"]
    return [
        (
            f"- {item.ecosystem}: changed={item.changed_files}, "
            f"source={item.source_files} files/{item.source_lines} lines, "
            f"tests={item.test_files} files/{item.test_lines} lines, "
            f"broad suppressions={item.broad_suppressions}"
        )
        for item in summaries
    ]


def _finding_lines(findings: tuple[ReviewabilityFinding, ...]) -> list[str]:
    """Render advisory reviewability findings."""
    if not findings:
        return ["- None"]
    return [
        f"- {item.ecosystem}/{item.kind}: {item.message} {item.recommendation}" for item in findings
    ]


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
