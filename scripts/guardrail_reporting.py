#!/usr/bin/env python3
"""Compact reporting helpers for guardrail verification."""

from __future__ import annotations

import json
from typing import Any


def nonblank_lines(text: str) -> list[str]:
    return [line.rstrip() for line in text.splitlines() if line.strip()]


def truncate_lines(lines: list[str], max_lines: int) -> list[str]:
    if len(lines) <= max_lines:
        return lines
    hidden = len(lines) - max_lines
    return [
        *lines[:max_lines],
        f"... {hidden} more lines omitted. See .verify-logs/ for full output.",
    ]


def truncate_chars(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n... output truncated. See .verify-logs/ for full output."


def compact_output(text: str, max_lines: int, max_chars: int) -> str:
    lines = nonblank_lines(text)
    if not lines:
        return "(no output)"
    return truncate_chars("\n".join(truncate_lines(lines, max_lines)), max_chars)


def pyright_summary_payload(payload: dict[str, object]) -> str | None:
    summary = payload.get("summary", {})
    return json.dumps(summary, indent=2) if summary else None


def format_diagnostic(diagnostic: dict[str, object]) -> str:
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
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None

    diagnostics = payload.get("generalDiagnostics", [])
    if not diagnostics:
        return pyright_summary_payload(payload)

    lines = [format_diagnostic(diagnostic) for diagnostic in diagnostics[:50]]

    omitted = len(diagnostics) - len(lines)
    if omitted > 0:
        lines.append(f"... {omitted} more diagnostics omitted. See .verify-logs/pyright.log")
    return "\n".join(lines)


def summarize_check(check_name: str, raw_output: str, max_lines: int, max_chars: int) -> str:
    if check_name == "pyright":
        pyright_summary = summarize_pyright(raw_output)
        if pyright_summary:
            return compact_output(pyright_summary, max_lines, max_chars)
    return compact_output(raw_output, max_lines, max_chars)


def print_skipped(skipped: list[Any], heading: str) -> None:
    if not skipped:
        return
    print(heading)
    for result in skipped:
        print(f"  {result.name}: {result.output}")


def print_success(skipped: list[Any]) -> None:
    print("PASS")
    print_skipped(skipped, "SKIPPED optional checks:")


def print_failures(profile: str, failures: list[Any], skipped: list[Any]) -> None:
    print(f"FAIL: {len(failures)} check(s) failed [{profile}]\n")
    for index, result in enumerate(failures, start=1):
        print(f"{index}. {result.name}")
        print(result.output or "(no output)")
        print()
    if skipped:
        print_skipped(skipped, "Skipped optional checks:")
        print()
    print("Full logs are in .verify-logs/.")
