"""Tests TypeScript exact repair fact extraction."""

from __future__ import annotations

import json
from pathlib import Path

from agent_context.failures import FailureRecord
from agent_maintainer.context.pack import exact_facts

APP_PATH = "src/app.ts"


# docsync:evidence.start evidence.typescript.repair_fact_tests
def test_typescript_typecheck_log_extracts_exact_fact(tmp_path: Path) -> None:
    """TypeScript compiler logs produce file, line, symbol facts."""
    log_path = tmp_path / "typescript-typecheck.log"
    log_path.write_text(
        f"{APP_PATH}(4,9): error TS2322: Type 'string' is not assignable\n",
        encoding="utf-8",
    )

    facts = exact_facts.repair_facts(
        tmp_path,
        (record("typescript-typecheck", log_path),),
    )

    assert facts == [
        {
            "check": "typescript-typecheck",
            "path": APP_PATH,
            "line": 4,
            "column": 9,
            "symbol": "TS2322",
            "message": "Type 'string' is not assignable",
            "severity": "error",
        },
    ]


def test_typescript_lint_log_extracts_eslint_json_fact(tmp_path: Path) -> None:
    """ESLint JSON logs produce exact lint repair facts."""
    log_path = tmp_path / "typescript-lint.log"
    log_path.write_text(
        json.dumps(
            [
                {
                    "filePath": APP_PATH,
                    "messages": [
                        {
                            "line": 7,
                            "column": 3,
                            "ruleId": "no-unused-vars",
                            "severity": 2,
                            "message": "Unused variable",
                        },
                    ],
                },
            ],
        ),
        encoding="utf-8",
    )

    facts = exact_facts.repair_facts(tmp_path, (record("typescript-lint", log_path),))

    assert facts == [
        {
            "check": "typescript-lint",
            "path": APP_PATH,
            "line": 7,
            "column": 3,
            "symbol": "no-unused-vars",
            "message": "Unused variable",
            "severity": "error",
        },
    ]


def test_typescript_test_log_extracts_jest_json_fact(tmp_path: Path) -> None:
    """Jest-compatible JSON test logs produce exact repair facts."""
    log_path = tmp_path / "typescript-test.log"
    log_path.write_text(
        json.dumps(
            {
                "testResults": [
                    {
                        "name": "tests/app.test.ts",
                        "assertionResults": [
                            {
                                "status": "failed",
                                "ancestorTitles": ["app"],
                                "title": "renders title",
                                "failureMessages": [
                                    "Error: expected heading to be visible\n"
                                    "    at tests/app.test.ts:9:3",
                                ],
                                "location": {"line": 9, "column": 3},
                            },
                        ],
                    },
                ],
            },
        ),
        encoding="utf-8",
    )

    facts = exact_facts.repair_facts(tmp_path, (record("typescript-test", log_path),))

    assert facts == [
        {
            "check": "typescript-test",
            "path": "tests/app.test.ts",
            "line": 9,
            "column": 3,
            "symbol": "typescript-test",
            "message": "app renders title: Error: expected heading to be visible",
            "severity": "error",
        },
    ]


def test_typescript_malformed_logs_fall_back_to_generic_fact(tmp_path: Path) -> None:
    """Malformed TypeScript output still yields generic failure facts."""
    log_path = tmp_path / "typescript-lint.log"
    log_path.write_text("{not-json", encoding="utf-8")

    facts = exact_facts.repair_facts(tmp_path, (record("typescript-lint", log_path),))

    assert facts == [
        {
            "check": "typescript-lint",
            "path": None,
            "line": None,
            "column": None,
            "symbol": None,
            "message": "typescript-lint failed with exit code 1",
            "severity": "error",
        },
    ]


def record(check: str, log_path: Path) -> FailureRecord:
    """Build failed check record with log path."""
    return FailureRecord(
        name=check,
        status="failed",
        category="test",
        priority=1,
        exit_code=1,
        log_path=str(log_path),
        log_bytes=log_path.stat().st_size,
        expansion_commands=(),
        artifact_paths=(),
    )


# docsync:evidence.end evidence.typescript.repair_fact_tests
