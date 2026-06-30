"""Advisory Technical Debt Score."""

from __future__ import annotations

import json
from pathlib import Path

from agent_maintainer.assess.debt_categories import (
    build_debt_categories,
    risk_label,
)
from agent_maintainer.assess.models import DebtCategory, DebtScoreReport, RepoEvidence
from agent_maintainer.config.schema import MaintainerConfig

DEBT_SCORE_JSON = "technical-debt-score.json"
DEBT_SCORE_MARKDOWN = "technical-debt-score.md"
LOW_RISK_MAX = 25
MODERATE_RISK_MAX = 50
HIGH_RISK_MAX = 75


def build_debt_report(
    evidence: RepoEvidence,
    config: MaintainerConfig,
    *,
    log_dir: Path,
) -> DebtScoreReport:
    """Build transparent advisory debt score."""

    categories = build_debt_categories(evidence, config, log_dir=log_dir)
    weighted = sum(category.score * category.weight for category in categories)
    total_weight = sum(category.weight for category in categories)
    score = round(weighted / total_weight)
    artifact_paths = (
        str(log_dir / DEBT_SCORE_JSON),
        str(log_dir / DEBT_SCORE_MARKDOWN),
    )
    return DebtScoreReport(
        target=evidence.target,
        score=score,
        risk=risk_label(score),
        confidence=_confidence(evidence, log_dir),
        summary=_summary(score),
        categories=categories,
        next_actions=_next_actions(categories),
        artifact_paths=artifact_paths,
        evidence=evidence,
    )


def write_debt_artifacts(report: DebtScoreReport, log_dir: Path) -> tuple[Path, Path]:
    """Write JSON and Markdown score artifacts."""

    log_dir.mkdir(parents=True, exist_ok=True)
    json_path = log_dir / DEBT_SCORE_JSON
    markdown_path = log_dir / DEBT_SCORE_MARKDOWN
    json_path.write_text(f"{json.dumps(_to_json(report), indent=2)}\n", encoding="utf-8")
    markdown_path.write_text(render_debt_markdown(report), encoding="utf-8")
    return json_path, markdown_path


def render_debt_markdown(report: DebtScoreReport) -> str:
    """Render scorecard Markdown."""

    lines = [
        "# Technical Debt Score",
        "",
        f"Score: **{report.score}/100** ({report.risk})",
        f"Confidence: **{report.confidence}**",
        "",
        report.summary,
        "",
        "## Categories",
        "",
    ]
    for category in report.categories:
        lines.extend(
            (
                f"### {category.name}: {category.score}/100",
                "",
                f"Status: {category.status}",
                "",
                "Evidence:",
                *[f"- {item}" for item in category.evidence],
                "",
                "Recommended next steps:",
                *[f"- {item}" for item in category.recommendations],
                "",
            ),
        )
    lines.extend(("## Next Actions", "", *[f"- {item}" for item in report.next_actions], ""))
    return "\n".join(lines)


def _summary(score: int) -> str:
    """Return plain-language score summary."""

    if score <= LOW_RISK_MAX:
        return "The repo has strong maintenance controls; focus on keeping ratchets fresh."
    if score <= MODERATE_RISK_MAX:
        return "The repo has useful controls with a few adoption gaps worth tightening."
    if score <= HIGH_RISK_MAX:
        return "The repo has meaningful debt risk; prioritize tests and boundaries."
    return "The repo should start with conservative ratchets before stricter gates."


def _confidence(evidence: RepoEvidence, log_dir: Path) -> str:
    """Return score confidence."""

    if evidence.has_agent_config and (log_dir / "manifest.json").exists():
        return "high"
    if evidence.has_agent_config and evidence.has_pyproject:
        return "medium"
    return "low"


def _next_actions(categories: tuple[DebtCategory, ...]) -> tuple[str, ...]:
    """Return next actions from the highest-risk categories."""

    highest = sorted(categories, key=lambda category: category.score, reverse=True)[:3]
    actions: list[str] = []
    for category in highest:
        actions.extend(category.recommendations[:1])
    return tuple(dict.fromkeys(actions))


def _to_json(report: DebtScoreReport) -> dict[str, object]:
    """Return stable JSON payload."""

    return {
        "target": report.target,
        "score": report.score,
        "risk": report.risk,
        "confidence": report.confidence,
        "summary": report.summary,
        "categories": [
            {
                "name": category.name,
                "score": category.score,
                "weight": category.weight,
                "status": category.status,
                "evidence": list(category.evidence),
                "recommendations": list(category.recommendations),
            }
            for category in report.categories
        ],
        "next_actions": list(report.next_actions),
        "artifact_paths": list(report.artifact_paths),
        "evidence": report.evidence.__dict__,
    }
