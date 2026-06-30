"""Compact reporting helpers for maintainer verification."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from agent_maintainer.context.budget import bound_text
from agent_maintainer.context.models import ContextBudget
from agent_maintainer.core.reporting_context import context_commands

PYRIGHT_DIAGNOSTIC_LIMIT = 50
STRUCTURED_DIAGNOSTIC_LIMIT = 50


def nonblank_lines(text: str) -> list[str]:
    """Return non-empty output lines without trailing whitespace."""

    return [line.rstrip() for line in text.splitlines() if line.strip()]


def truncate_lines(lines: list[str], max_lines: int) -> list[str]:
    """Limit output by line count while pointing readers to raw logs."""

    if len(lines) <= max_lines:
        return lines
    hidden = len(lines) - max_lines
    return [
        *lines[:max_lines],
        f"... {hidden} more lines omitted. See .verify-logs/ for full output.",
    ]


def truncate_chars(text: str, max_chars: int) -> str:
    """Limit output by character count while preserving a log pointer."""

    if len(text) <= max_chars:
        return text
    truncated_text = text[:max_chars].rstrip()
    return f"{truncated_text}\n... output truncated. See .verify-logs/ for full output."


def compact_output(text: str, max_lines: int, max_chars: int) -> str:
    """Return a concise human-readable summary of command output."""

    lines = nonblank_lines(text)
    if not lines:
        return "(no output)"
    bounded = bound_text(
        "\n".join(lines),
        ContextBudget(max_chars=max_chars, max_items=max_lines, max_lines=max_lines),
    )
    if not bounded.truncated:
        return bounded.text
    return "\n".join(
        (
            bounded.text.rstrip(),
            (
                "... output omitted "
                f"{bounded.omitted_chars} chars and {bounded.omitted_lines} lines. "
                "Full output is in .verify-logs/."
            ),
        )
    )


def pyright_summary_payload(payload: dict[str, object]) -> str | None:
    """Return Pyright summary JSON when no diagnostics are present."""

    summary = payload.get("summary", {})
    return json.dumps(summary, indent=2) if summary else None


def format_diagnostic(diagnostic: dict[str, object]) -> str:
    """Format one Pyright diagnostic as a compact editor-style line."""

    file_name = diagnostic.get("file", "<unknown>")
    range_info = diagnostic.get("range", {})
    start = range_info.get("start", {}) if isinstance(range_info, dict) else {}
    line = int(start.get("line", 0)) + 1 if isinstance(start, dict) else 1
    character = int(start.get("character", 0)) + 1 if isinstance(start, dict) else 1
    severity = diagnostic.get("severity", "error")
    message = diagnostic.get("message", "")
    rule = diagnostic.get("rule")
    suffix = f" [{rule}]" if rule else ""
    return f"{file_name}:{line}:{character}: {severity}: {message}{suffix}"


def summarize_pyright(raw: str) -> str | None:
    """Summarize Pyright JSON output, falling back when parsing fails."""

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None

    diagnostics = payload.get("generalDiagnostics", [])
    if not diagnostics:
        return pyright_summary_payload(payload)

    lines = [format_diagnostic(diagnostic) for diagnostic in diagnostics[:PYRIGHT_DIAGNOSTIC_LIMIT]]

    omitted = len(diagnostics) - len(lines)
    if omitted > 0:
        lines.append(f"... {omitted} more diagnostics omitted. See .verify-logs/pyright.log")
    return "\n".join(lines)


def summarize_check_from_artifacts(
    check_name: str,
    artifact_paths: tuple[str, ...],
    raw_output: str,
    max_lines: int,
    max_chars: int,
) -> str:
    """Summarize failed check, preferring known structured artifacts."""

    artifact_summary = structured_artifact_summary(check_name, artifact_paths)
    if artifact_summary:
        return compact_output(artifact_summary, max_lines, max_chars)
    return summarize_check(check_name, raw_output, max_lines, max_chars)


def structured_artifact_summary(check_name: str, artifact_paths: tuple[str, ...]) -> str | None:
    """Return compact summary from known structured diagnostic artifacts."""

    if check_name == "pyright":
        return summarize_json_artifact(artifact_paths, "pyright.json", summarize_pyright_payload)
    if check_name == "ruff":
        return summarize_json_artifact(artifact_paths, "ruff.json", summarize_ruff_payload)
    if check_name == "bandit":
        return summarize_json_artifact(artifact_paths, "bandit.json", summarize_bandit_payload)
    return None


def summarize_json_artifact(
    artifact_paths: tuple[str, ...],
    suffix: str,
    formatter: Callable[[object], str | None],
) -> str | None:
    """Load matching JSON artifact and return formatter output if possible."""

    path = next((Path(item) for item in artifact_paths if item.endswith(suffix)), None)
    if path is None or not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return formatter(payload)


def summarize_pyright_payload(payload: object) -> str | None:
    """Summarize Pyright JSON artifact payload."""

    if not isinstance(payload, dict):
        return None
    return summarize_pyright(json.dumps(payload))


def summarize_ruff_payload(payload: object) -> str | None:
    """Summarize Ruff JSON artifact payload."""

    if not isinstance(payload, list):
        return None
    diagnostics = [item for item in payload if isinstance(item, dict)]
    lines = [format_ruff_diagnostic(item) for item in diagnostics[:STRUCTURED_DIAGNOSTIC_LIMIT]]
    omitted = len(diagnostics) - len(lines)
    if omitted > 0:
        lines.append(f"... {omitted} more diagnostics omitted. See .verify-logs/ruff.json")
    return "\n".join(lines) if lines else None


def format_ruff_diagnostic(diagnostic: dict[str, object]) -> str:
    """Format one Ruff diagnostic compact editor-style line."""

    location = diagnostic.get("location", {})
    row = location.get("row", 1) if isinstance(location, dict) else 1
    column = location.get("column", 1) if isinstance(location, dict) else 1
    filename = diagnostic.get("filename", "<unknown>")
    code = diagnostic.get("code", "ruff")
    message = diagnostic.get("message", "")
    return f"{filename}:{row}:{column}: {code}: {message}"


def summarize_bandit_payload(payload: object) -> str | None:
    """Summarize Bandit JSON artifact payload."""

    if not isinstance(payload, dict):
        return None
    raw_results = payload.get("results", [])
    if not isinstance(raw_results, list):
        return None
    findings = [item for item in raw_results if isinstance(item, dict)]
    lines = [format_bandit_finding(item) for item in findings[:STRUCTURED_DIAGNOSTIC_LIMIT]]
    omitted = len(findings) - len(lines)
    if omitted > 0:
        lines.append(f"... {omitted} more findings omitted. See .verify-logs/bandit.json")
    return "\n".join(lines) if lines else None


def format_bandit_finding(finding: dict[str, object]) -> str:
    """Format one Bandit finding compact editor-style line."""

    filename = finding.get("filename", "<unknown>")
    line_number = finding.get("line_number", 1)
    test_id = finding.get("test_id", "bandit")
    severity = finding.get("issue_severity", "UNKNOWN")
    message = finding.get("issue_text", "")
    return f"{filename}:{line_number}: {test_id} {severity}: {message}"


def summarize_check(check_name: str, raw_output: str, max_lines: int, max_chars: int) -> str:
    """Summarize a failed check with check-specific formatting when available."""

    if check_name == "pyright":
        pyright_summary = summarize_pyright(raw_output)
        if pyright_summary:
            return compact_output(pyright_summary, max_lines, max_chars)
    return compact_output(raw_output, max_lines, max_chars)


def print_skipped(skipped: list[Any], heading: str) -> None:
    """Print skipped optional checks under a supplied heading."""

    if not skipped:
        return
    print(heading)
    for result in skipped:
        print(f"  {result.name}: {result.output}")


def print_warnings(warnings: list[Any], heading: str) -> None:
    """Print successful checks that still produced actionable warnings."""

    if not warnings:
        return
    print(heading)
    for result in warnings:
        print(f"  {result.name}: {result.output}")


def print_success(
    skipped: list[Any],
    warnings: list[Any] | None = None,
    *,
    run_details: tuple[str, ...] = (),
) -> None:
    """Print the passing verifier result, warnings, and optional skips."""

    print("PASS")
    for detail in run_details:
        print(detail)
    print_warnings(warnings or [], "WARNINGS:")
    print_skipped(skipped, "SKIPPED optional checks:")


def print_failures(
    profile: str,
    failures: list[Any],
    skipped: list[Any],
    *,
    run_details: tuple[str, ...] = (),
    footer: tuple[str | None, str | None] = (None, None),
) -> None:
    """Print a compact failure report for the selected verifier profile."""

    context_log_dir, rerun_command = footer
    print(f"FAIL: {len(failures)} check(s) failed [{profile}]\n")
    for detail in run_details:
        print(detail)
    if run_details:
        print()
    failed_names = ", ".join(result.name for result in failures)
    print(f"Failed checks: {failed_names}\n")
    for index, result in enumerate(failures, start=1):
        print(f"{index}. {result.name}")
        print(result.output or "(no output)")
        print("Next context:")
        for command in context_commands(result.name, log_dir=context_log_dir):
            print(f"  {command}")
        print()
    if skipped:
        print_skipped(skipped, "Skipped optional checks:")
        print()
    logs_dir = context_log_dir or ".verify-logs/"
    rerun_command = rerun_command or f"python3 -m agent_maintainer verify --profile {profile}"
    print(f"Full logs are in {logs_dir}.")
    print(f"Smallest rerun after fixes: `{rerun_command}`")
