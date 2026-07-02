"""Strict agent-facing repair capsule rendering."""

from __future__ import annotations

from typing import Any

from agent_maintainer.core.reporting_context import context_commands

DEFAULT_FAILURE_LIMIT = 3


def render_failure_capsule(
    *,
    profile: str,
    failures: list[Any],
    run_details: tuple[str, ...],
    context_log_dir: str | None,
    rerun_command: str | None,
) -> list[str]:
    """Return strict repair-capsule lines for failed verification."""

    command = rerun_command or f"python3 -m agent_maintainer verify --profile {profile}"
    run_id = detail_value(run_details, "Run ID:") or "unavailable"
    lines = [
        "Result: FAIL",
        f"Profile: {profile}",
        f"Run ID: {run_id}",
        "",
        "Top repair facts:",
        *top_repair_fact_lines(failures),
        "",
        "Likely next action:",
        command,
        "",
        "Expand only if needed:",
        expansion_command(failures, log_dir=context_log_dir),
    ]
    return lines


def detail_value(details: tuple[str, ...], prefix: str) -> str | None:
    """Return value from a `Label: value` run-detail line."""

    for detail in details:
        if detail.startswith(prefix):
            return detail.removeprefix(prefix).strip()
    return None


def top_repair_fact_lines(
    failures: list[Any],
    *,
    limit: int = DEFAULT_FAILURE_LIMIT,
) -> list[str]:
    """Return bounded numbered repair facts for agent-facing output."""

    lines = [
        f"{index}. {repair_fact_line(result)}"
        for index, result in enumerate(failures[:limit], start=1)
    ]
    omitted = len(failures) - limit
    if omitted > 0:
        lines.append(f"... {omitted} more failed check(s).")
    return lines or ["1. (no failed checks)"]


def repair_fact_line(result: Any) -> str:
    """Return one compact repair fact line for a failed check."""

    message = first_nonblank_line(str(result.output or "")) or "(no output)"
    return f"{result.name}: {message}"


def first_nonblank_line(text: str) -> str:
    """Return first non-empty line without trailing whitespace."""

    for line in text.splitlines():
        if line.strip():
            return line.rstrip()
    return ""


def expansion_command(failures: list[Any], *, log_dir: str | None) -> str:
    """Return one bounded context expansion command."""

    if not failures:
        return "python -m agent_maintainer context failures --limit 20"
    commands = context_commands(failures[0].name, log_dir=log_dir)
    if commands:
        return commands[0]
    return "python -m agent_maintainer context failures --limit 20"
