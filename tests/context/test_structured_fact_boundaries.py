"""Boundary tests for structured exact repair-fact artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from agent_repair_facts.registry import artifact_facts_from_text

RUFF_LINE = 7
RUFF_COLUMN = 3
BANDIT_LINE = 12
COVERAGE_MISSING_LINE = 44
APP_PATH = "src/pkg/app.py"


def test_structured_artifact_parsers_skip_non_object_entries() -> None:
    """Mixed arrays keep valid repair facts without trusting malformed entries."""

    cases: tuple[tuple[str, str, object, str], ...] = (
        (
            "ruff",
            "ruff.json",
            [
                None,
                {
                    "filename": APP_PATH,
                    "location": {"row": RUFF_LINE, "column": RUFF_COLUMN},
                    "code": "F401",
                    "message": "Unused import",
                },
            ],
            "F401",
        ),
        (
            "pyright",
            "pyright.json",
            {
                "generalDiagnostics": [
                    7,
                    {
                        "file": APP_PATH,
                        "rule": "reportUnknownMemberType",
                        "message": "Unknown member",
                    },
                ],
            },
            "reportUnknownMemberType",
        ),
        (
            "bandit",
            "bandit.json",
            {
                "results": [
                    "invalid",
                    {
                        "filename": APP_PATH,
                        "line_number": BANDIT_LINE,
                        "test_id": "B101",
                        "issue_text": "Assert used",
                    },
                ],
            },
            "B101",
        ),
        (
            "pytest-coverage",
            "coverage.json",
            {
                "files": {
                    "ignored.py": [],
                    APP_PATH: {"missing_lines": [COVERAGE_MISSING_LINE]},
                },
            },
            "coverage",
        ),
    )

    for check, filename, payload, expected_symbol in cases:
        facts = artifact_facts_from_text(
            check,
            Path(filename),
            json.dumps(payload),
        )

        assert facts[0]["symbol"] == expected_symbol
