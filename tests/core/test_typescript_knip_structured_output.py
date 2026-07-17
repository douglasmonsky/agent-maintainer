"""Tests bounded structured summaries for TypeScript Knip output."""

from __future__ import annotations

import json

import pytest

from agent_maintainer.core import reporting, structured_typescript

KNIP_SUMMARY_LINE_LIMIT = 50


# docsync:evidence.start evidence.typescript.knip_summary_tests
def test_typescript_knip_output_summarizes_supported_findings() -> None:
    """Knip JSON output produces deterministic editor-style summaries."""

    raw_output = json.dumps(
        {
            "issues": [
                {
                    "file": "src/api.ts",
                    "exports": [{"name": "unusedExport", "line": 8, "col": 3}],
                    "cycles": [{"name": "ignored"}],
                },
                {"file": "src/unused.ts", "files": [{"name": "src/unused.ts"}]},
            ]
        }
    )

    summary = structured_typescript.summarize_typescript_check(
        "typescript-knip:web", raw_output
    )

    assert summary == (
        "src/api.ts:8:3: error: knip-unused-export: Unused export: unusedExport\n"
        "src/unused.ts: error: knip-unused-file: Unused file: src/unused.ts"
    )
    assert reporting.summarize_check("typescript-knip:web", raw_output, 5, 500) == summary


def test_typescript_knip_summary_is_bounded_with_omission_marker() -> None:
    """Knip summaries reserve the fiftieth line for the omission marker."""

    exports = [{"name": f"export-{index:03d}"} for index in range(51)]
    raw_output = json.dumps({"issues": [{"file": "src/api.ts", "exports": exports}]})

    summary = structured_typescript.summarize_typescript_check("typescript-knip", raw_output)

    assert summary is not None
    lines = summary.splitlines()
    assert len(lines) == KNIP_SUMMARY_LINE_LIMIT
    assert lines[0].endswith("Unused export: export-000")
    assert lines[-1] == "... 2 more Knip findings omitted. See .verify-logs/"


def test_typescript_knip_summary_counts_findings_beyond_the_fact_cap() -> None:
    """The omission count includes findings dropped by the 500-fact cap."""

    exports = [{"name": f"export-{index:03d}"} for index in range(501)]
    raw_output = json.dumps({"issues": [{"file": "src/api.ts", "exports": exports}]})

    summary = structured_typescript.summarize_typescript_check("typescript-knip", raw_output)

    assert summary is not None
    lines = summary.splitlines()
    assert len(lines) == KNIP_SUMMARY_LINE_LIMIT
    assert lines[-1] == "... 452 more Knip findings omitted. See .verify-logs/"


@pytest.mark.parametrize("raw_output", ["{not-json", "[]", "{}", '{"issues": {}}'])
def test_typescript_knip_invalid_output_has_no_structured_summary(raw_output: str) -> None:
    """Invalid Knip output falls back to the normal bounded raw-output path."""

    assert structured_typescript.summarize_typescript_check("typescript-knip", raw_output) is None
# docsync:evidence.end evidence.typescript.knip_summary_tests
