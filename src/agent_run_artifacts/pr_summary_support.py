"""Support helpers for GitHub PR verification summaries."""

from __future__ import annotations

from collections.abc import Sequence

from agent_context.budget import bound_text
from agent_context.models import ContextBudget
from agent_run_artifacts.models import CheckResultLike, RunContextLike

MAX_PR_SUMMARY_CHARS = 12_000
MAX_FAILURES = 5
MAX_OUTPUT_LINES = 4
MAX_SUMMARY_LINES = 180


def summary_expansion_commands(check_name: str) -> list[str]:
    """Return stable context expansion commands for one failed check."""

    return [
        f"python -m agent_maintainer context failures --check {check_name} --limit 20",
        f"python -m agent_maintainer context log {check_name} --tail 120",
    ]


def summary_rerun_command(context: RunContextLike) -> str:
    """Return canonical command to rerun verifier profile."""

    command = [
        "python3",
        "-m",
        "agent_maintainer",
        "verify",
        "--profile",
        context.profile,
        "--base-ref",
        context.base_ref,
        "--compare-branch",
        context.compare_branch,
    ]
    if context.staged:
        command.append("--staged")
    return " ".join(command)


def failed_results(results: Sequence[CheckResultLike]) -> list[CheckResultLike]:
    """Return failed check results."""

    return [result for result in results if not result.passed]


def matching_results(
    results: Sequence[CheckResultLike],
    names: tuple[str, ...],
) -> list[CheckResultLike]:
    """Return results matching any supplied name fragment."""

    return [result for result in results if any(name in result.name for name in names)]


def first_result(results: Sequence[CheckResultLike], name: str) -> CheckResultLike | None:
    """Return first result by exact name."""

    return next((result for result in results if result.name == name), None)


def result_status_lines(results: Sequence[CheckResultLike]) -> list[str]:
    """Return compact result status bullets."""

    return [f"- `{result.name}`: `{result_state(result)}`" for result in results]


def result_state(result: CheckResultLike) -> str:
    """Return compact result state for summary."""

    if result.skipped:
        return result.skip_status or "skipped"
    if not result.passed:
        return "failed"
    if result.warning:
        return "warning"
    return "passed"


def compact_output_bullets(output: str) -> list[str]:
    """Return compact output as markdown bullet lines."""

    return [f"- {line}" for line in compact_output_lines(output)]


def compact_output_lines(output: str) -> list[str]:
    """Return compact non-empty output lines."""

    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return []
    return lines[:MAX_OUTPUT_LINES]


def bounded_summary(text: str, context: RunContextLike) -> str:
    """Return bounded summary markdown."""

    max_chars = min(MAX_PR_SUMMARY_CHARS, context.config.context_last_failure_budget_chars)
    bounded = bound_text(
        text,
        ContextBudget(
            max_chars=max_chars,
            max_items=context.config.context_max_failure_items,
            max_lines=MAX_SUMMARY_LINES,
        ),
    )
    if not bounded.truncated:
        return f"{bounded.text}\n"
    note = (
        "\n\n... PR summary omitted "
        f"{bounded.omitted_chars} chars and {bounded.omitted_lines} lines. "
        "See `.verify-logs/manifest.json` and `.verify-logs/LAST_FAILURE.md`."
    )
    summary_text = bounded.text.rstrip()
    preserved = preserved_expansion_footer(text, summary_text)
    return f"{summary_text}{note}{preserved}\n"


def preserved_expansion_footer(original_text: str, bounded_text: str) -> str:
    """Return command footer when truncation hides repair commands."""
    commands = [
        line.strip()
        for line in original_text.splitlines()
        if "python -m agent_maintainer context" in line and line.strip()
    ]
    hidden_commands = [command for command in commands if command not in bounded_text]
    if not hidden_commands:
        return ""
    command_lines = "\n".join(hidden_commands)
    return f"\n\n## Preserved Expansion Commands\n{command_lines}"
