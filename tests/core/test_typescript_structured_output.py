"""Tests TypeScript structured output summaries."""

from __future__ import annotations

import json

from agent_maintainer.core import reporting, structured_typescript
from agent_maintainer.ecosystems.typescript import diagnostics

APP_PATH = "src/app.ts"


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
