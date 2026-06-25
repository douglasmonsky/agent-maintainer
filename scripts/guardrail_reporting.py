"""Compact reporting helpers for guardrail verification."""

from __future__ import annotations

import json
from typing import Any

PYRIGHT_DIAGNOSTIC_LIMIT = 50


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
    return truncate_chars("\n".join(truncate_lines(lines, max_lines)), max_chars)


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


def print_success(skipped: list[Any], warnings: list[Any] | None = None) -> None:
    """Print the passing verifier result, warnings, and optional skips."""

    print("PASS")
    print_warnings(warnings or [], "WARNINGS:")
    print_skipped(skipped, "SKIPPED optional checks:")


def print_failures(profile: str, failures: list[Any], skipped: list[Any]) -> None:
    """Print a compact failure report for the selected verifier profile."""

    print(f"FAIL: {len(failures)} check(s) failed [{profile}]\n")
    for index, result in enumerate(failures, start=1):
        print(f"{index}. {result.name}")
        print(result.output or "(no output)")
        print()
    if skipped:
        print_skipped(skipped, "Skipped optional checks:")
        print()
    print("Full logs are in .verify-logs/.")
