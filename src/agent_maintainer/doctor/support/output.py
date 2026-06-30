"""Doctor output formatting and exit status helpers."""

from __future__ import annotations

import json
from collections.abc import Iterable

from agent_maintainer.doctor.support.models import ERROR, WARNING, DoctorResult


def results_to_jsonable(results: Iterable[DoctorResult]) -> list[dict[str, str]]:
    """Return doctor results as plain dictionaries for JSON output."""

    return [result.__dict__ for result in results]


def json_text(results: Iterable[DoctorResult]) -> str:
    """Return formatted JSON output for doctor results."""

    return json.dumps(results_to_jsonable(results), indent=2)


def format_text_row(result: DoctorResult) -> str:
    """Format one compact PASS/WARN/FAIL doctor row."""

    hint = f" Hint: {result.hint}" if result.hint else ""
    return f"{result.status} {result.name} [{result.state}]: {result.message}{hint}"


def print_text(results: Iterable[DoctorResult]) -> None:
    """Print doctor results as compact PASS/WARN/FAIL rows."""

    for result in results:
        print(format_text_row(result))


def status_code(results: Iterable[DoctorResult], *, strict: bool) -> int:
    """Return the doctor process status for default or strict mode."""

    items = tuple(results)
    if any(result.status == ERROR for result in items):
        return 1
    if strict and any(result.status == WARNING for result in items):
        return 1
    return 0
