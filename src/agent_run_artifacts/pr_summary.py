"""Render bounded GitHub PR verification summaries."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from agent_run_artifacts import pr_summary_support as summary_support
from agent_run_artifacts.models import CheckResultLike, RunContextLike

PR_SUMMARY_NAME = "pr-summary.md"
DEBT_SCORE_NAME = "technical-debt-score.json"
DEBT_SCORE_COMMAND = "python -m agent_maintainer assess debt"
DEBT_DRIVER_LIMIT = 3


def render_pr_summary(
    *,
    log_dir: Path,
    context: RunContextLike,
    results: Sequence[CheckResultLike],
) -> str:
    """Return bounded GitHub step summary markdown."""

    sections = (
        header_lines(),
        verification_result_lines(context, results),
        technical_debt_score_lines(log_dir),
        top_failure_lines(results),
        test_intelligence_lines(context, results),
        ratchet_target_lines(context),
        change_budget_lines(results),
        change_plan_lines(context, results),
        context_pack_lines(log_dir, context),
        expansion_command_lines(results),
    )
    text = "\n".join(line for section in sections for line in (*section, ""))
    return summary_support.bounded_summary(text.rstrip(), context)


def header_lines() -> list[str]:
    """Return summary heading lines."""

    return ["# Agent Maintainer Verification Summary"]


def verification_result_lines(
    context: RunContextLike,
    results: Sequence[CheckResultLike],
) -> list[str]:
    """Return overall verification result section."""

    result = "FAIL" if summary_support.failed_results(results) else "PASS"
    return [
        "## Verification Result",
        f"- Result: **{result}**",
        f"- Profile: `{context.profile}`",
        f"- Base ref: `{context.base_ref}`",
        f"- Compare branch: `{context.compare_branch}`",
        f"- Rerun: `{summary_support.summary_rerun_command(context)}`",
    ]


def technical_debt_score_lines(log_dir: Path) -> list[str]:
    """Return current technical debt score summary lines."""

    lines = ["## Technical Debt Score"]
    score_path = log_dir / DEBT_SCORE_NAME
    if not score_path.exists():
        return [
            *lines,
            "- Status: `not run`",
            f"- Run: `{DEBT_SCORE_COMMAND}`",
        ]

    try:
        payload = json.loads(score_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [
            *lines,
            "- Status: `unreadable`",
            f"- Re-run: `{DEBT_SCORE_COMMAND}`",
            f"- Artifact: `{score_path.as_posix()}`",
        ]

    score = payload.get("score", "unknown")
    risk = payload.get("risk", "unknown")
    confidence = payload.get("confidence", "unknown")
    summary = payload.get("summary")
    interpretation = payload.get("interpretation")
    debt_lines = [
        *lines,
        f"- Score: `{score}/100` (`{risk}` risk, `{confidence}` confidence)",
    ]
    if isinstance(summary, str) and summary:
        debt_lines.append(f"- Summary: {summary}")
    if isinstance(interpretation, str) and interpretation:
        debt_lines.append(f"- Interpretation: {interpretation}")
    debt_lines.extend(_debt_category_summary_lines(payload))
    debt_lines.append(f"- Artifact: `{score_path.as_posix()}`")
    return debt_lines


def _debt_category_summary_lines(payload: dict[str, object]) -> list[str]:
    """Return compact debt category driver lines."""

    categories = payload.get("categories")
    if not isinstance(categories, list):
        return []

    drivers = sorted(
        (category for category in categories if isinstance(category, dict)),
        key=_debt_category_rank,
        reverse=True,
    )
    if not drivers:
        return []

    lines = ["- Top debt drivers:"]
    for category in drivers[:DEBT_DRIVER_LIMIT]:
        name = category.get("name", "unknown")
        score = category.get("score", "unknown")
        status = category.get("status", "unknown")
        lines.append(f"  - `{name}`: `{score}/100` (`{status}`)")
    return lines


def _debt_category_rank(category: dict[object, object]) -> tuple[int, int]:
    """Return category sort key for debt driver summary."""

    score = category.get("score")
    weight = category.get("weight")
    return (
        score if isinstance(score, int) else -1,
        weight if isinstance(weight, int) else -1,
    )


def top_failure_lines(results: Sequence[CheckResultLike]) -> list[str]:
    """Return top failed checks section."""

    failures = summary_support.failed_results(results)
    lines = ["## Top Failures"]
    if not failures:
        return [*lines, "- No failed checks."]
    for failure in failures[: summary_support.MAX_FAILURES]:
        lines.extend(failure_lines(failure))
    omitted = len(failures) - summary_support.MAX_FAILURES
    if omitted > 0:
        lines.append(f"- {omitted} additional failure(s) omitted.")
    return lines


def failure_lines(failure: CheckResultLike) -> list[str]:
    """Return summary lines for one failed check."""

    lines = [
        f"- `{failure.name}` failed with exit code `{failure.exit_code}`.",
        f"  - Log: `{failure.log_path}`",
    ]
    lines.extend(f"  - {line}" for line in summary_support.compact_output_lines(failure.output))
    return lines


def test_intelligence_lines(
    context: RunContextLike,
    results: Sequence[CheckResultLike],
) -> list[str]:
    """Return test-intelligence section."""

    lines = [
        "## Test Intelligence",
        (
            "- Changed-source map: "
            f"`python -m agent_maintainer test-intel changed --base-ref {context.base_ref}`"
        ),
    ]
    related = summary_support.matching_results(
        results,
        ("pytest", "coverage", "diff-cover", "change-budget"),
    )
    if not related:
        return [*lines, "- No test-intelligence-related check output in this run."]
    lines.extend(summary_support.result_status_lines(related))
    return lines


def ratchet_target_lines(context: RunContextLike) -> list[str]:
    """Return ratchet target section."""

    lines = ["## Ratchet Targets"]
    if not context.config.ratchet_enabled:
        return [*lines, "- Ratchet mode disabled for this repository."]
    base_ref = context.base_ref
    baseline_path = context.config.ratchet_baseline_path
    next_command = "python -m agent_maintainer ratchet next --base-ref"
    return [
        *lines,
        f"- Next targets: `{next_command} {base_ref}`",
        f"- Baseline: `{baseline_path}`",
    ]


def change_budget_lines(results: Sequence[CheckResultLike]) -> list[str]:
    """Return change-budget section."""

    lines = ["## Change Budget"]
    budget_result = summary_support.first_result(results, "change-budget")
    if budget_result is None:
        return [*lines, "- Change-budget check did not run in this profile."]
    status = summary_support.result_state(budget_result)
    return [
        *lines,
        f"- Status: `{status}`",
        *summary_support.compact_output_bullets(budget_result.output),
    ]


def change_plan_lines(
    context: RunContextLike,
    results: Sequence[CheckResultLike],
) -> list[str]:
    """Return change-plan status section."""

    lines = ["## Change Plan Status"]
    if context.config.large_changes_enabled:
        lines.append("- Configured large-change plans are enabled.")
    else:
        lines.append("- Large-change plans are disabled unless a check opts into them.")
    budget_result = summary_support.first_result(results, "change-budget")
    if budget_result is not None and "change plan" in budget_result.output.lower():
        lines.extend(summary_support.compact_output_bullets(budget_result.output))
    lines.append("- Check plans: `python -m agent_maintainer change-plan check`")
    return lines


def context_pack_lines(log_dir: Path, context: RunContextLike) -> list[str]:
    """Return context pack artifact section."""

    pack_path = log_dir / "context" / "PACK.md"
    lines = ["## Context Pack Path"]
    if pack_path.exists():
        lines.append(f"- Context pack: `{pack_path.as_posix()}`")
    else:
        lines.append("- Context pack not generated in this run.")
    pack_budget = context.config.context_pack_budget_chars
    command = f"python -m agent_maintainer context pack --budget {pack_budget}"
    lines.append(f"- Generate one: `{command}`")
    return lines


def expansion_command_lines(results: Sequence[CheckResultLike]) -> list[str]:
    """Return expansion commands section."""

    lines = ["## Expansion Commands"]
    failures = summary_support.failed_results(results)
    if not failures:
        return [*lines, "- No failure expansion commands needed."]
    commands = [
        command
        for failure in failures[: summary_support.MAX_FAILURES]
        for command in summary_support.summary_expansion_commands(failure.name)
    ]
    lines.extend(f"- `{command}`" for command in commands)
    return lines
