"""Parse TypeScript and JavaScript coverage artifacts."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from typing import cast

from agent_repair_facts.parsers.typescript_diagnostics import (
    JsonObject,
    TypeScriptDiagnostic,
    optional_int,
    optional_text,
)

LCOV_LINE_RE = re.compile(r"^DA:(?P<line>\d+),(?P<hits>-?\d+)(?:,.*)?$")
MAX_LCOV_SOURCE_CHARS = 1_000


@dataclass(frozen=True)
class LcovFileRecord:
    """Executable and covered line numbers for one LCOV source value."""

    source: str
    executable_lines: frozenset[int]
    covered_lines: frozenset[int]


def parse_coverage_summary_json(raw_output: str) -> list[TypeScriptDiagnostic]:
    """Parse Istanbul coverage-summary JSON output."""
    try:
        payload = json.loads(raw_output)
    except (json.JSONDecodeError, RecursionError):
        return []
    return coverage_summary_diagnostics(payload)


def parse_lcov_info(raw_output: str) -> list[TypeScriptDiagnostic]:
    """Parse LCOV coverage output."""

    diagnostics: list[TypeScriptDiagnostic] = []
    for record in parse_lcov_records(raw_output):
        missing_lines = sorted(record.executable_lines - record.covered_lines)
        diagnostics.extend(lcov_record_diagnostics(record.source, missing_lines))
    return diagnostics


def parse_lcov_records(raw_output: str) -> tuple[LcovFileRecord, ...]:
    """Return deterministic executable-line records from LCOV text."""

    line_sets: dict[str, tuple[set[int], set[int]]] = {}
    current_source: str | None = None

    for raw_line in raw_output.splitlines():
        line = raw_line.strip()
        if line.startswith("SF:"):
            current_source = safe_lcov_source(line.removeprefix("SF:"))
            if current_source is not None:
                line_sets.setdefault(current_source, (set(), set()))
            continue
        if line == "end_of_record":
            current_source = None
            continue
        match = LCOV_LINE_RE.match(line)
        if match is None or current_source is None:
            continue
        line_number = int(match.group("line"))
        if line_number <= 0:
            continue
        executable_lines, covered_lines = line_sets[current_source]
        executable_lines.add(line_number)
        if int(match.group("hits")) > 0:
            covered_lines.add(line_number)

    return tuple(
        LcovFileRecord(
            source=source,
            executable_lines=frozenset(executable_lines),
            covered_lines=frozenset(covered_lines),
        )
        for source, (executable_lines, covered_lines) in sorted(line_sets.items())
    )


def safe_lcov_source(value: str) -> str | None:
    """Return a bounded source scalar without Unicode control characters."""

    source = optional_text(value)
    if source is None or source == "." or len(source) > MAX_LCOV_SOURCE_CHARS:
        return None
    if any(unicodedata.category(character).startswith("C") for character in source):
        return None
    return source


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
