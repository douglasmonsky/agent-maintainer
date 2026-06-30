"""Parse log-only exact repair facts."""

from __future__ import annotations

import re
from pathlib import Path

from agent_maintainer.context.pack.fact_payloads import (
    fact_payload,
    python_location_from_text,
)

FILE_LENGTH_RE = re.compile(r"^(?P<path>[^:\n]+\.py): (?P<message>.+)$")
CHANGE_BUDGET_BLOCK_RE = re.compile(r"^BLOCK:\s*(?P<message>.+)$")


def file_length_facts(path: Path, check: str) -> list[dict[str, object]]:
    """Return exact facts from file-length log output."""

    return [
        fact_payload(
            {
                "check": check,
                "path": match.group("path"),
                "line": None,
                "column": None,
                "symbol": "file-length",
                "message": match.group("message"),
                "severity": "error",
            },
        )
        for match in log_matches(path, FILE_LENGTH_RE)
    ]


def change_budget_facts(path: Path, check: str) -> list[dict[str, object]]:
    """Return exact facts from change-budget log output."""

    return [
        change_budget_fact(check, match.group("message"))
        for match in log_matches(path, CHANGE_BUDGET_BLOCK_RE)
    ]


def change_budget_fact(check: str, message: str) -> dict[str, object]:
    """Return one change-budget exact fact."""

    location = python_location_from_text(message)
    return fact_payload(
        {
            "check": check,
            "path": location.get("path"),
            "line": location.get("line"),
            "column": None,
            "symbol": "change-budget",
            "message": message,
            "severity": "error",
        },
    )


def log_matches(path: Path, pattern: re.Pattern[str]) -> list[re.Match[str]]:
    """Return regex matches for stripped log lines."""

    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return [match for line in lines if (match := pattern.match(line.strip()))]
