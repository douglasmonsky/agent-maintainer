"""Tests exact repair facts from Knip JSON reporter output."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_repair_facts import registry

FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "typescript_knip"
EXPECTED_SUPPORTED_FINDINGS = 11
KNIP_FACT_LIMIT = 500


def log_facts(check: str, raw_output: str) -> list[dict[str, object]]:
    """Parse in-memory Knip log output through the public registry."""

    return registry.log_facts_from_text(check, Path("typescript-knip.log"), raw_output)


# docsync:evidence.start evidence.typescript.knip_fact_tests
def test_knip_supported_categories_emit_deterministic_facts() -> None:
    """Supported Knip categories normalize after deterministic sorting."""

    facts = log_facts(
        "typescript-knip",
        (FIXTURE_ROOT / "supported-issues.json").read_text(encoding="utf-8"),
    )

    assert len(facts) == EXPECTED_SUPPORTED_FINDINGS
    assert [(fact["path"], fact["symbol"], fact["message"]) for fact in facts] == [
        ("src/api.ts", "knip-unused-binary", "Unused binary: tsx"),
        ("src/api.ts", "knip-unused-dependency", "Unused dependency: left-pad"),
        ("src/api.ts", "knip-unused-dependency", "Unused dependency: vitest"),
        ("src/api.ts", "knip-unused-export", "Unused export: unusedExport"),
        (
            "src/api.ts",
            "knip-unused-export",
            "Unused export: unusedNamespaceExport",
        ),
        (
            "src/api.ts",
            "knip-unused-type",
            "Unused type: UnusedNamespaceType",
        ),
        (
            "src/api.ts",
            "knip-unused-dependency",
            "Unused dependency: react-dom",
        ),
        ("src/api.ts", "knip-unused-type", "Unused type: UnusedType"),
        (
            "src/api.ts",
            "knip-unlisted-dependency",
            "Unlisted dependency: missing-package",
        ),
        ("src/api.ts", "knip-unresolved", "Unresolved import or binary: ./missing"),
        ("src/unused.ts", "knip-unused-file", "Unused file: src/unused.ts"),
    ]
    assert facts[1] == {
        "check": "typescript-knip",
        "path": "src/api.ts",
        "line": 2,
        "column": 5,
        "symbol": "knip-unused-dependency",
        "message": "Unused dependency: left-pad",
        "severity": "error",
    }
    assert facts[0]["line"] is None
    assert facts[0]["column"] is None


def test_knip_workspace_check_preserves_full_check_name() -> None:
    """Workspace Knip facts keep the stable suffixed check name."""

    raw_output = json.dumps(
        {"issues": [{"file": "apps/web/src/a.ts", "exports": [{"name": "a"}]}]}
    )

    facts = log_facts("typescript-knip:web", raw_output)

    assert facts[0]["check"] == "typescript-knip:web"
    assert facts[0]["path"] == "apps/web/src/a.ts"


@pytest.mark.parametrize(
    "raw_output",
    [
        "{not-json",
        "[]",
        "{}",
        '{"issues": {}}',
        '{"issues": [null, {}, {"file": 12}, {"file": "src/a.ts", "exports": {}}]}',
    ],
)
def test_knip_invalid_payloads_emit_no_facts(raw_output: str) -> None:
    """Invalid roots, groups, and category arrays fail closed."""

    assert log_facts("typescript-knip", raw_output) == []


def test_knip_malformed_items_do_not_hide_valid_neighbors() -> None:
    """Malformed items are skipped without discarding valid findings."""

    raw_output = json.dumps(
        {
            "issues": [
                {
                    "file": "src/a.ts",
                    "exports": [None, "bad", {}, {"name": "valid", "line": True}],
                }
            ]
        }
    )

    facts = log_facts("typescript-knip", raw_output)

    assert len(facts) == 1
    assert facts[0]["message"] == "Unused export: valid"
    assert facts[0]["line"] is None


def test_knip_facts_sort_before_the_retention_limit() -> None:
    """The first 500 sorted findings are retained regardless of input order."""

    exports = [{"name": f"export-{index:03d}"} for index in range(KNIP_FACT_LIMIT, -1, -1)]
    raw_output = json.dumps({"issues": [{"file": "src/api.ts", "exports": exports}]})

    facts = log_facts("typescript-knip", raw_output)

    assert len(facts) == KNIP_FACT_LIMIT
    assert facts[0]["message"] == "Unused export: export-000"
    assert facts[-1]["message"] == "Unused export: export-499"


@pytest.mark.parametrize(
    ("check", "raw_output", "expected_symbol"),
    [
        (
            "typescript-lint:web",
            json.dumps(
                [
                    {
                        "filePath": "apps/web/src/app.ts",
                        "messages": [
                            {
                                "line": 2,
                                "column": 3,
                                "ruleId": "no-unused-vars",
                                "severity": 2,
                                "message": "Unused variable",
                            }
                        ],
                    }
                ]
            ),
            "no-unused-vars",
        ),
        (
            "typescript-typecheck:web",
            "apps/web/src/app.ts(2,3): error TS2322: Type mismatch",
            "TS2322",
        ),
        (
            "typescript-test:web",
            json.dumps(
                {
                    "testResults": [
                        {
                            "name": "apps/web/src/app.test.ts",
                            "assertionResults": [
                                {
                                    "status": "failed",
                                    "title": "renders",
                                    "failureMessage": "Expected heading",
                                }
                            ],
                        }
                    ]
                }
            ),
            "typescript-test",
        ),
    ],
)
def test_existing_typescript_workspace_checks_use_root_parsers(
    check: str,
    raw_output: str,
    expected_symbol: str,
) -> None:
    """Known workspace checks share parsers while retaining their check names."""

    facts = log_facts(check, raw_output)

    assert facts[0]["check"] == check
    assert facts[0]["symbol"] == expected_symbol


def test_check_family_normalization_does_not_broaden_other_checks() -> None:
    """Only known TypeScript check families accept workspace suffixes."""

    assert log_facts("ruff:web", "[]") == []
# docsync:evidence.end evidence.typescript.knip_fact_tests
