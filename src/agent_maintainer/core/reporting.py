"""Compact reporting helpers for maintainer verification."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from agent_context.budget import bound_text
from agent_context.models import ContextBudget
from agent_maintainer.core.repair_capsule import render_failure_capsule
from agent_maintainer.core.structured_artifacts import (
    structured_artifact_summary as expanded_artifact_summary,
)
from agent_maintainer.core.structured_typescript import (
    summarize_typescript_check,
)
from agent_maintainer.core.structured_values import (
    json_array,
    json_object,
    json_objects,
    plain_int,
)

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
    range_info = json_object(diagnostic.get("range", {})) or {}
    start = json_object(range_info.get("start", {})) or {}
    line = plain_int(start.get("line")) + 1
    character = plain_int(start.get("character")) + 1
    severity = diagnostic.get("severity", "error")
    message = diagnostic.get("message", "")
    rule = diagnostic.get("rule")
    suffix = f" [{rule}]" if rule else ""
    return f"{file_name}:{line}:{character}: {severity}: {message}{suffix}"


def summarize_pyright(raw: str) -> str | None:
    """Summarize Pyright JSON output, falling back when parsing fails."""

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    payload = json_object(parsed)
    if payload is None:
        return None

    diagnostic_values = json_array(payload.get("generalDiagnostics", []))
    if diagnostic_values is None:
        return None
    diagnostics = json_objects(diagnostic_values)
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
    return expanded_artifact_summary(check_name, artifact_paths)


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

    report = json_object(payload)
    if report is None:
        return None
    return summarize_pyright(json.dumps(report))


def summarize_ruff_payload(payload: object) -> str | None:
    """Summarize Ruff JSON artifact payload."""

    values = json_array(payload)
    if values is None:
        return None
    diagnostics = json_objects(values)
    lines = [format_ruff_diagnostic(item) for item in diagnostics[:STRUCTURED_DIAGNOSTIC_LIMIT]]
    omitted = len(diagnostics) - len(lines)
    if omitted > 0:
        lines.append(f"... {omitted} more diagnostics omitted. See .verify-logs/ruff.json")
    return "\n".join(lines) if lines else None


def format_ruff_diagnostic(diagnostic: dict[str, object]) -> str:
    """Format one Ruff diagnostic compact editor-style line."""

    location = json_object(diagnostic.get("location", {})) or {}
    row = location.get("row", 1)
    column = location.get("column", 1)
    filename = diagnostic.get("filename", "<unknown>")
    code = diagnostic.get("code", "ruff")
    message = diagnostic.get("message", "")
    return f"{filename}:{row}:{column}: {code}: {message}"


def summarize_bandit_payload(payload: object) -> str | None:
    """Summarize Bandit JSON artifact payload."""

    report = json_object(payload)
    if report is None:
        return None
    raw_results = json_array(report.get("results", []))
    if raw_results is None:
        return None
    findings = json_objects(raw_results)
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
    typescript_summary = summarize_typescript_check(check_name, raw_output)
    if typescript_summary:
        return compact_output(typescript_summary, max_lines, max_chars)
    return compact_output(raw_output, max_lines, max_chars)


def print_skipped(skipped: list[Any], heading: str) -> None:
    """Print skipped optional checks under a supplied heading."""

    if not skipped:
        return
    print(heading)
    for result in skipped:
        status = getattr(result, "skip_status", "") or "skipped"
        print(f"  {result.name} [{status}]: {result.output}")


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
    _skipped: list[Any],
    *,
    run_details: tuple[str, ...] = (),
    footer: tuple[str | None, str | None] = (None, None),
) -> None:
    """Print strict repair capsule for failed verifier output."""

    context_log_dir, rerun_command = footer
    for line in render_failure_capsule(
        profile=profile,
        failures=failures,
        run_details=run_details,
        context_log_dir=context_log_dir,
        rerun_command=rerun_command,
    ):
        print(line)
