"""Tests TypeScript structured output summaries."""

from __future__ import annotations

import json

from agent_maintainer.core import reporting, structured_typescript
from agent_maintainer.ecosystems.typescript import diagnostics

APP_PATH = "src/app.ts"
EXPECTED_VITEST_FAILURES = 2
EXPECTED_FLOAT_VALUE = 75.5


# docsync:evidence.start evidence.typescript.structured_output_tests
def test_typescript_typecheck_output_summarizes_tsc_diagnostics() -> None:
    """TypeScript compiler text diagnostics produce compact summaries."""
    raw_output = f"{APP_PATH}(4,9): error TS2322: Type 'string' is not assignable"

    summary = structured_typescript.summarize_typescript_typecheck(raw_output)

    assert summary == (f"{APP_PATH}:4:9: error: TS2322: Type 'string' is not assignable")
    assert reporting.summarize_check("typescript-typecheck", raw_output, 5, 500) == summary


def test_typescript_lint_output_summarizes_eslint_json() -> None:
    """ESLint JSON output produces compact summaries."""
    raw_output = json.dumps(
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
    )

    summary = structured_typescript.summarize_typescript_lint(raw_output)

    assert summary == f"{APP_PATH}:7:3: error: no-unused-vars: Unused variable"
    assert reporting.summarize_check("typescript-lint", raw_output, 5, 500) == summary


def test_typescript_workspace_lint_uses_the_root_structured_summary() -> None:
    """Workspace suffixes do not disable TypeScript structured parsing."""

    raw_output = json.dumps(
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
                    }
                ],
            }
        ]
    )

    summary = structured_typescript.summarize_typescript_check(
        "typescript-lint:web", raw_output
    )

    assert summary == f"{APP_PATH}:7:3: error: no-unused-vars: Unused variable"


def test_typescript_test_output_summarizes_jest_json() -> None:
    """Jest-compatible JSON test output produces compact summaries."""
    raw_output = json.dumps(
        {
            "testResults": [
                {
                    "name": "tests/app.test.ts",
                    "assertionResults": [
                        {
                            "status": "failed",
                            "fullName": "app renders the title",
                            "failureMessages": [
                                "Error: expected heading to be visible\n    at app.test.ts:9:3",
                            ],
                            "location": {"line": 9, "column": 3},
                        },
                    ],
                },
            ],
        },
    )

    summary = structured_typescript.summarize_typescript_test(raw_output)

    assert summary == (
        "tests/app.test.ts:9:3: error: typescript-test: "
        "app renders the title: Error: expected heading to be visible"
    )
    assert reporting.summarize_check("typescript-test", raw_output, 5, 500) == summary


def test_typescript_test_output_summarizes_vitest_task_json() -> None:
    """Vitest task-style JSON output produces compact summaries."""
    raw_output = json.dumps(
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
    )

    summary = structured_typescript.summarize_typescript_test(raw_output)

    assert summary == (
        "apps/web/src/App.test.tsx:14:5: error: typescript-test: "
        "renders marketing headline: expected title to include Welcome"
    )


def test_typescript_test_output_summarizes_istanbul_coverage_summary() -> None:
    """Istanbul coverage-summary JSON output produces compact summaries."""
    raw_output = json.dumps(
        {
            "total": {"lines": {"total": 20, "covered": 19, "pct": 95}},
            "apps/web/src/App.tsx": {
                "lines": {"total": 8, "covered": 6, "pct": 75},
                "statements": {"total": 10, "covered": 8, "pct": 80},
                "branches": {"total": 2, "covered": 1, "pct": 50},
                "functions": {"total": 2, "covered": 2, "pct": 100},
            },
        }
    )

    summary = structured_typescript.summarize_typescript_test(raw_output)

    assert summary == (
        "apps/web/src/App.tsx:1:1: error: typescript-coverage: "
        "Coverage below 100%: lines 75.00% (6/8), "
        "statements 80.00% (8/10), branches 50.00% (1/2)"
    )


def test_typescript_test_output_summarizes_lcov() -> None:
    """LCOV output produces compact TypeScript coverage summaries."""
    raw_output = "SF:apps/web/src/App.tsx\nDA:3,1\nDA:8,0\nDA:9,0\nend_of_record\n"

    summary = structured_typescript.summarize_typescript_test(raw_output)

    assert summary == (
        "apps/web/src/App.tsx:8:1: error: typescript-coverage: 2 uncovered line(s) in file."
    )


def test_vitest_parser_handles_error_fallbacks_and_invalid_payloads() -> None:
    """Vitest parser keeps useful failures while ignoring unsupported tasks."""
    raw_output = json.dumps(
        {
            "files": [
                None,
                {"filepath": "tests/bad.test.ts", "tasks": "bad"},
                {
                    "file": "tests/fallback.test.ts",
                    "tasks": [
                        None,
                        {"name": "passes", "result": {"state": "pass"}},
                        {
                            "name": "uses stack",
                            "result": {
                                "state": "failed",
                                "errors": [
                                    {
                                        "stack": (
                                            "AssertionError: stack fallback\n"
                                            "    at tests/fallback.test.ts:4:2"
                                        )
                                    }
                                ],
                            },
                        },
                        {
                            "name": "no error details",
                            "result": {"state": "fail", "errors": []},
                        },
                        {"name": "missing result"},
                    ],
                },
            ]
        }
    )

    diagnostics_payload = diagnostics.parse_vitest_json(raw_output)

    assert diagnostics.parse_vitest_json("[]") == []
    assert len(diagnostics_payload) == EXPECTED_VITEST_FAILURES
    assert diagnostics_payload[0].path == "tests/fallback.test.ts"
    assert diagnostics_payload[0].message == ("uses stack: AssertionError: stack fallback")
    assert diagnostics_payload[1].message == "no error details"


def test_coverage_parsers_handle_edge_cases() -> None:
    """Coverage parsers ignore complete files and compute missing percentages."""
    summary = json.dumps(
        {
            "apps/web/src/Complete.tsx": {"lines": {"total": 2, "covered": 2, "pct": 100}},
            "apps/web/src/Partial.tsx": {
                "lines": {"total": 4, "covered": 2},
                "statements": "bad",
            },
        }
    )
    lcov_without_terminal_record = (
        "SF:apps/web/src/First.tsx\nDA:2,0\nSF:apps/web/src/Second.tsx\nDA:3,0\n"
    )

    summary_diagnostics = diagnostics.parse_coverage_summary_json(summary)
    lcov_diagnostics = diagnostics.parse_lcov_info(lcov_without_terminal_record)

    assert diagnostics.parse_coverage_summary_json("[]") == []
    assert diagnostics.parse_lcov_info("SF:apps/web/src/Clean.tsx\nDA:1,1\n") == []
    assert summary_diagnostics[0].message == ("Coverage below 100%: lines 50.00% (2/4)")
    assert [item.path for item in lcov_diagnostics] == [
        "apps/web/src/First.tsx",
        "apps/web/src/Second.tsx",
    ]
    assert diagnostics.optional_float(True) is None
    assert diagnostics.optional_float("bad") is None
    assert diagnostics.optional_float("75.5") == EXPECTED_FLOAT_VALUE


def test_typescript_test_parser_ignores_non_failure_payloads() -> None:
    """Jest-compatible parser ignores unsupported and passing payloads."""
    raw_output = json.dumps(
        {
            "testResults": [
                {"name": "tests/missing.test.ts"},
                {
                    "name": "tests/app.test.ts",
                    "assertionResults": [
                        None,
                        {"status": "passed", "fullName": "app renders title"},
                    ],
                },
            ],
        },
    )

    assert diagnostics.parse_jest_json("[]") == []
    assert diagnostics.parse_jest_json(json.dumps({"testResults": [None]})) == []
    assert diagnostics.parse_jest_json(json.dumps({"testResults": "bad"})) == []
    assert diagnostics.parse_jest_json(raw_output) == []


def test_typescript_test_parser_uses_fallback_failure_message() -> None:
    """Jest-compatible parser handles missing location and failureMessages."""
    raw_output = json.dumps(
        {
            "testResults": [
                {
                    "name": "tests/app.test.ts",
                    "assertionResults": [
                        {
                            "status": "failed",
                            "title": "renders title",
                            "failureMessage": "Expected heading to be visible",
                        },
                    ],
                },
            ],
        },
    )

    diagnostic = diagnostics.parse_jest_json(raw_output)[0]

    assert diagnostic.path == "tests/app.test.ts"
    assert diagnostic.line is None
    assert diagnostic.column is None
    assert diagnostic.message == "renders title: Expected heading to be visible"


def test_typescript_test_parser_uses_suite_fallback_message() -> None:
    """Jest-compatible parser uses suite message when assertion lacks details."""
    raw_output = json.dumps(
        {
            "testResults": [
                {
                    "name": "tests/app.test.ts",
                    "message": "Suite failed before assertions",
                    "assertionResults": [
                        {
                            "status": "failed",
                            "failureMessages": ["", "   "],
                        },
                    ],
                },
            ],
        },
    )

    diagnostic = diagnostics.parse_jest_json(raw_output)[0]

    assert diagnostic.message == "Suite failed before assertions"


def test_typescript_test_parser_uses_title_when_message_missing() -> None:
    """Jest-compatible parser keeps failed title when no message exists."""
    raw_output = json.dumps(
        {
            "testResults": [
                {
                    "name": "tests/app.test.ts",
                    "assertionResults": [
                        {
                            "status": "failed",
                            "title": "renders title",
                            "failureMessages": ["", "   "],
                        },
                    ],
                },
            ],
        },
    )

    diagnostic = diagnostics.parse_jest_json(raw_output)[0]

    assert diagnostic.message == "renders title"


def test_typescript_summary_falls_back_for_malformed_output() -> None:
    """Malformed TypeScript output leaves raw-summary fallback intact."""
    raw_output = "{not-json"

    assert structured_typescript.summarize_typescript_lint(raw_output) is None
    assert structured_typescript.summarize_typescript_typecheck(raw_output) is None
    assert structured_typescript.summarize_typescript_test(raw_output) is None
    assert reporting.summarize_check("typescript-lint", raw_output, 5, 500) == raw_output


# docsync:evidence.end evidence.typescript.structured_output_tests
