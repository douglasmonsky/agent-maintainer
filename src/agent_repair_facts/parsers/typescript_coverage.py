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
MAX_LCOV_LINE_CHARS = 1_000
MAX_LCOV_INTEGER_CHARS = 20


@dataclass(frozen=True)
class LcovFileRecord:
    """Executable and covered line numbers for one LCOV source value."""

    source: str
    executable_lines: frozenset[int]
    covered_lines: frozenset[int]


@dataclass
class _LcovLineSets:
    """Mutable executable and covered line sets during parsing."""

    executable: set[int]
    covered: set[int]


@dataclass
class _LcovParseState:
    """Current source and accumulated records during LCOV parsing."""

    records: dict[str, _LcovLineSets]
    source: str | None = None


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

    state = _LcovParseState(records={})
    for raw_line in raw_output.splitlines():
        line = raw_line.strip()
        if len(line) <= MAX_LCOV_LINE_CHARS:
            update_lcov_state(state, line)

    return tuple(
        LcovFileRecord(
            source=source,
            executable_lines=frozenset(line_sets.executable),
            covered_lines=frozenset(line_sets.covered),
        )
        for source, line_sets in sorted(state.records.items())
    )


def update_lcov_state(state: _LcovParseState, line: str) -> None:
    """Consume one supported LCOV line into mutable parser state."""

    if line.startswith("SF:"):
        state.source = safe_lcov_source(line.removeprefix("SF:"))
        if state.source is not None:
            state.records.setdefault(state.source, _LcovLineSets(set(), set()))
        return
    if line == "end_of_record":
        state.source = None
        return
    add_lcov_data_line(state, LCOV_LINE_RE.match(line))


def add_lcov_data_line(state: _LcovParseState, match: re.Match[str] | None) -> None:
    """Add one valid DA line to the current source record."""

    if match is None or state.source is None:
        return
    line_number = bounded_lcov_int(match.group("line"))
    hits = bounded_lcov_int(match.group("hits"))
    if line_number is None or hits is None or line_number <= 0:
        return
    line_sets = state.records[state.source]
    line_sets.executable.add(line_number)
    if hits > 0:
        line_sets.covered.add(line_number)


def bounded_lcov_int(value: str) -> int | None:
    """Return a bounded LCOV integer without invoking huge conversions."""

    if len(value.removeprefix("-")) > MAX_LCOV_INTEGER_CHARS:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def safe_lcov_source(value: str) -> str | None:
    """Return a bounded source scalar without Unicode control characters."""

    source = optional_text(value)
    if source is None:
        return None
    source_text = str(source)
    if source_text == "." or len(source_text) > MAX_LCOV_SOURCE_CHARS:
        return None
    if any(
        unicodedata.category(source_text[index]).startswith("C")
        for index in range(len(source_text))
    ):
        return None
    return source_text


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
