"""Parse log-only exact repair facts."""

from __future__ import annotations

import re
from pathlib import Path

from agent_repair_facts.payloads import (
    fact_payload,
    python_location_from_text,
)

FILE_LENGTH_RE = re.compile(r"^(?P<path>[^:\n]+\.py): (?P<message>.+)$")
CHANGE_BUDGET_BLOCK_RE = re.compile(r"^BLOCK:\s*(?P<message>.+)$")
ARCHITECTURE_DECISION_RE = re.compile(
    r"^architecture policy changed without decision note:\s*(?P<path>.+)$",
)
RUFF_FORMAT_RE = re.compile(r"^Would reformat:\s*(?P<path>.+)$")
WEMAKE_RE = re.compile(
    r"^(?P<path>[^:\n]+\.py):(?P<line>\d+):(?P<column>\d+):\s*"
    r"(?P<symbol>WPS\d+)\s*(?P<message>.+)$",
)
XENON_BLOCK_RE = re.compile(
    r'^ERROR:xenon:block "(?P<path>[^:\n]+\.py):(?P<line>\d+) '
    r'(?P<symbol>[^"]+)" (?P<message>.+)$',
)
PATH_FIELD = "path"
LINE_FIELD = "line"
MESSAGE_FIELD = "message"
SYMBOL_FIELD = "symbol"


def file_length_facts(path: Path, check: str) -> list[dict[str, object]]:
    """Return exact facts from file-length log output."""

    return [
        log_fact(
            check,
            {
                PATH_FIELD: match.group(PATH_FIELD),
                SYMBOL_FIELD: "file-length",
                MESSAGE_FIELD: match.group(MESSAGE_FIELD),
            },
        )
        for match in log_matches(path, FILE_LENGTH_RE)
    ]


def change_budget_facts(path: Path, check: str) -> list[dict[str, object]]:
    """Return exact facts from change-budget log output."""

    return [
        change_budget_fact(check, match.group(MESSAGE_FIELD))
        for match in log_matches(path, CHANGE_BUDGET_BLOCK_RE)
    ]


def change_budget_fact(check: str, message: str) -> dict[str, object]:
    """Return one change-budget exact fact."""

    location = python_location_from_text(message)
    return log_fact(
        check,
        {
            PATH_FIELD: location.get(PATH_FIELD),
            LINE_FIELD: location.get(LINE_FIELD),
            SYMBOL_FIELD: "change-budget",
            MESSAGE_FIELD: message,
        },
    )


def architecture_decision_facts(path: Path, check: str) -> list[dict[str, object]]:
    """Return exact facts from architecture decision-note log output."""

    return [
        log_fact(
            check,
            {
                PATH_FIELD: match.group(PATH_FIELD),
                SYMBOL_FIELD: "architecture-decision",
                MESSAGE_FIELD: ("Add or update a decision note for architecture policy change."),
            },
        )
        for match in log_matches(path, ARCHITECTURE_DECISION_RE)
    ]


def ruff_format_facts(path: Path, check: str) -> list[dict[str, object]]:
    """Return exact facts from ruff format check output."""

    return [
        log_fact(
            check,
            {
                PATH_FIELD: match.group(PATH_FIELD),
                SYMBOL_FIELD: "ruff-format",
                MESSAGE_FIELD: "Run ruff format on this file.",
            },
        )
        for match in log_matches(path, RUFF_FORMAT_RE)
    ]


def wemake_facts(path: Path, check: str) -> list[dict[str, object]]:
    """Return exact facts from wemake flake8 log output."""

    return [
        log_fact(
            check,
            {
                PATH_FIELD: match.group(PATH_FIELD),
                LINE_FIELD: int(match.group(LINE_FIELD)),
                "column": int(match.group("column")),
                SYMBOL_FIELD: match.group(SYMBOL_FIELD),
                MESSAGE_FIELD: match.group(MESSAGE_FIELD),
            },
        )
        for match in log_matches(path, WEMAKE_RE)
    ]


def xenon_complexity_facts(path: Path, check: str) -> list[dict[str, object]]:
    """Return exact facts from xenon complexity gate output."""

    return [
        log_fact(
            check,
            {
                PATH_FIELD: match.group(PATH_FIELD),
                LINE_FIELD: int(match.group(LINE_FIELD)),
                SYMBOL_FIELD: match.group(SYMBOL_FIELD),
                MESSAGE_FIELD: match.group(MESSAGE_FIELD),
            },
        )
        for match in log_matches(path, XENON_BLOCK_RE)
    ]


def log_fact(check: str, values: dict[str, object]) -> dict[str, object]:
    """Return one normalized log-parser fact payload."""

    payload: dict[str, object] = {
        "check": check,
        PATH_FIELD: None,
        LINE_FIELD: None,
        "column": None,
        SYMBOL_FIELD: None,
        MESSAGE_FIELD: None,
        "severity": "error",
    }
    payload.update(values)
    return fact_payload(payload)


def log_matches(path: Path, pattern: re.Pattern[str]) -> list[re.Match[str]]:
    """Return regex matches for stripped log lines."""

    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return [match for line in lines if (match := pattern.match(line.strip()))]
