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


def test_typescript_test_log_extracts_vitest_task_json_fact(tmp_path: Path) -> None:
    """Vitest task-style JSON test logs produce exact repair facts."""
    log_path = tmp_path / "typescript-test.log"
    log_path.write_text(
        json.dumps(
            {
                "files": [
                    {
                        "filepath": "apps/web/src/App.test.tsx",
                        "tasks": [
                            {
                                "name": "renders marketing headline",
                                "result": {
                                    "state": "fail",
                                    "errors": [
                                        {
                                            "message": "expected title to include Welcome",
                                            "location": {"line": 14, "column": 5},
                                        }
                                    ],
                                },
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    facts = exact_facts.repair_facts(tmp_path, (record("typescript-test", log_path),))

    assert facts == [
        {
            "check": "typescript-test",
            "path": "apps/web/src/App.test.tsx",
            "line": 14,
            "column": 5,
            "symbol": "typescript-test",
            "message": "renders marketing headline: expected title to include Welcome",
            "severity": "error",
        },
    ]


def test_typescript_test_coverage_summary_artifact_extracts_fact(
    tmp_path: Path,
) -> None:
    """Istanbul coverage-summary artifacts produce exact coverage facts."""
    artifact_path = tmp_path / "coverage-summary.json"
    artifact_path.write_text(
        json.dumps(
            {
                "total": {"lines": {"total": 20, "covered": 19, "pct": 95}},
                "apps/web/src/App.tsx": {
                    "lines": {"total": 8, "covered": 6, "pct": 75},
                    "statements": {"total": 10, "covered": 8, "pct": 80},
                    "branches": {"total": 2, "covered": 1, "pct": 50},
                    "functions": {"total": 2, "covered": 2, "pct": 100},
                },
            }
        ),
        encoding="utf-8",
    )

    facts = exact_facts.repair_facts(
        tmp_path,
        (record_with_artifact("typescript-test", artifact_path),),
    )

    assert facts == [
        {
            "check": "typescript-test",
            "path": "apps/web/src/App.tsx",
            "line": None,
            "column": None,
            "symbol": "typescript-coverage",
            "message": (
                "Coverage below 100%: lines 75.00% (6/8), "
                "statements 80.00% (8/10), branches 50.00% (1/2)"
            ),
            "severity": "error",
        },
    ]


def test_typescript_test_lcov_artifact_extracts_missing_line_fact(
    tmp_path: Path,
) -> None:
    """LCOV artifacts produce exact TypeScript coverage facts."""
    artifact_path = tmp_path / "lcov.info"
    artifact_path.write_text(
        "SF:apps/web/src/App.tsx\nDA:3,1\nDA:8,0\nDA:9,0\nend_of_record\n",
        encoding="utf-8",
    )

    facts = exact_facts.repair_facts(
        tmp_path,
        (record_with_artifact("typescript-test", artifact_path),),
    )

    assert facts == [
        {
            "check": "typescript-test",
            "path": "apps/web/src/App.tsx",
            "line": 8,
            "column": None,
            "symbol": "typescript-coverage",
            "message": "2 uncovered line(s) in file.",
            "severity": "error",
        },
    ]


def test_typescript_test_unknown_artifact_falls_back_to_generic_fact(
    tmp_path: Path,
) -> None:
    """Unsupported TypeScript test artifacts keep generic failure facts."""
    artifact_path = tmp_path / "coverage.xml"
    artifact_path.write_text("<coverage />", encoding="utf-8")

    facts = exact_facts.repair_facts(
        tmp_path,
        (record_with_artifact("typescript-test", artifact_path),),
    )

    assert facts == [
        {
            "check": "typescript-test",
            "path": None,
            "line": None,
            "column": None,
            "symbol": None,
            "message": "typescript-test failed with exit code 1",
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


def record_with_artifact(check: str, artifact_path: Path) -> FailureRecord:
    """Build failed check record with artifact path."""
    return FailureRecord(
        name=check,
        status="failed",
        category="test",
        priority=1,
        exit_code=1,
        log_path=str(artifact_path.with_suffix(".log")),
        log_bytes=0,
        expansion_commands=(),
        artifact_paths=(str(artifact_path),),
    )


# docsync:evidence.end evidence.typescript.repair_fact_tests
