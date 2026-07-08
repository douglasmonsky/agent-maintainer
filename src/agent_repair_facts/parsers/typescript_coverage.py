"""Parse TypeScript and JavaScript coverage artifacts."""

from __future__ import annotations

import json
import re
from typing import cast

from agent_repair_facts.parsers.typescript_diagnostics import (
    JsonObject,
    TypeScriptDiagnostic,
    optional_int,
    optional_text,
)

LCOV_LINE_RE = re.compile(r"^DA:(?P<line>\d+),(?P<hits>-?\d+)(?:,.*)?$")


def parse_coverage_summary_json(raw_output: str) -> list[TypeScriptDiagnostic]:
    """Parse Istanbul coverage-summary JSON output."""
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError:
        return []
    return coverage_summary_diagnostics(payload)


def parse_lcov_info(raw_output: str) -> list[TypeScriptDiagnostic]:
    """Parse LCOV coverage output."""
    diagnostics: list[TypeScriptDiagnostic] = []
    current_path: str | None = None
    missing_lines: list[int] = []

    for raw_line in raw_output.splitlines():
        line = raw_line.strip()
        if line.startswith("SF:"):
            if current_path is not None:
                diagnostics.extend(lcov_record_diagnostics(current_path, missing_lines))
            current_path = optional_text(line.removeprefix("SF:"))
            missing_lines = []
            continue
        if line == "end_of_record":
            if current_path is not None:
                diagnostics.extend(lcov_record_diagnostics(current_path, missing_lines))
            current_path = None
            missing_lines = []
            continue
        match = LCOV_LINE_RE.match(line)
        if match and int(match.group("hits")) == 0:
            missing_lines.append(int(match.group("line")))

    if current_path is not None:
        diagnostics.extend(lcov_record_diagnostics(current_path, missing_lines))
    return diagnostics


def coverage_summary_diagnostics(payload: object) -> list[TypeScriptDiagnostic]:
    """Return diagnostics from Istanbul coverage-summary payloads."""
    if not isinstance(payload, dict):
        return []

    diagnostics: list[TypeScriptDiagnostic] = []
    for file_path, file_payload in cast(JsonObject, payload).items():
        if file_path == "total" or not isinstance(file_payload, dict):
            continue
        diagnostic = coverage_summary_diagnostic(str(file_path), cast(JsonObject, file_payload))
        if diagnostic is not None:
            diagnostics.append(diagnostic)
    return diagnostics


def coverage_summary_diagnostic(
    file_path: str,
    file_payload: JsonObject,
) -> TypeScriptDiagnostic | None:
    """Return one coverage summary diagnostic for a file."""
    metric_messages = [
        metric_message(metric_name, file_payload.get(metric_name))
        for metric_name in ("lines", "statements", "branches", "functions")
    ]
    visible_messages = [message for message in metric_messages if message]
    if not visible_messages:
        return None
    coverage_details = ", ".join(visible_messages)
    return TypeScriptDiagnostic(
        path=file_path,
        line=None,
        column=None,
        code="typescript-coverage",
        message=f"Coverage below 100%: {coverage_details}",
        severity="error",
    )


def metric_message(metric_name: str, value: object) -> str | None:
    """Return a compact coverage metric message when uncovered code remains."""
    if not isinstance(value, dict):
        return None
    metric = cast(JsonObject, value)
    total = optional_int(metric.get("total"))
    covered = optional_int(metric.get("covered"))
    pct = optional_float(metric.get("pct"))
    if total is None or covered is None or total <= covered:
        return None
    if pct is None:
        pct = covered / total * 100
    return f"{metric_name} {pct:.2f}% ({covered}/{total})"


def lcov_record_diagnostics(
    file_path: str,
    missing_lines: list[int],
) -> list[TypeScriptDiagnostic]:
    """Return a diagnostic for one LCOV file record."""
    if not missing_lines:
        return []
    return [
        TypeScriptDiagnostic(
            path=file_path,
            line=missing_lines[0],
            column=None,
            code="typescript-coverage",
            message=f"{len(missing_lines)} uncovered line(s) in file.",
            severity="error",
        )
    ]


def optional_float(value: object) -> float | None:
    """Return float values from diagnostic fields."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None
