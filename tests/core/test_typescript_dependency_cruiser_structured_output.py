"""Tests bounded dependency-cruiser structured summaries."""

from __future__ import annotations

import json

from agent_maintainer.core import structured_typescript

SUMMARY_LINE_LIMIT = 50


# docsync:evidence.start evidence.typescript.dependency_cruiser_summary_tests
def test_dependency_cruiser_summary_formats_one_violation() -> None:
    """Workspace checks route through the shared architecture parser."""

    summary = structured_typescript.summarize_typescript_check(
        "typescript-dependency-cruiser:web",
        json.dumps(_payload_with_findings(1)),
    )

    assert summary == (
        "src/000.ts -> src/target.ts: rule-000 [error; dependency]"
    )


def test_dependency_cruiser_summary_reserves_the_final_line() -> None:
    """The fiftieth line truthfully reports all omitted findings."""

    summary = structured_typescript.summarize_typescript_check(
        "typescript-dependency-cruiser",
        json.dumps(_payload_with_findings(51)),
    )

    assert summary is not None
    lines = summary.splitlines()
    assert len(lines) == SUMMARY_LINE_LIMIT
    assert lines[-1] == (
        "... 2 more dependency-cruiser findings omitted. See .verify-logs/"
    )


def test_dependency_cruiser_summary_counts_beyond_parser_retention() -> None:
    """The omission count uses the pre-slice supported total."""

    summary = structured_typescript.summarize_typescript_check(
        "typescript-dependency-cruiser",
        json.dumps(_payload_with_findings(600)),
    )

    assert summary is not None
    lines = summary.splitlines()
    assert len(lines) == SUMMARY_LINE_LIMIT
    assert lines[-1] == (
        "... 551 more dependency-cruiser findings omitted. See .verify-logs/"
    )


def test_dependency_cruiser_invalid_output_has_no_summary() -> None:
    """Unsupported output keeps the bounded raw-log fallback available."""

    assert (
        structured_typescript.summarize_typescript_check(
            "typescript-dependency-cruiser",
            "{not-json",
        )
        is None
    )


def _payload_with_findings(count: int) -> dict[str, object]:
    """Build deterministic dependency-cruiser summary violations."""

    return {
        "summary": {
            "violations": [
                {
                    "from": f"src/{index:03d}.ts",
                    "to": "src/target.ts",
                    "type": "dependency",
                    "rule": {
                        "name": f"rule-{index:03d}",
                        "severity": "error",
                    },
                }
                for index in range(count)
            ]
        },
        "modules": [],
    }


# docsync:evidence.end evidence.typescript.dependency_cruiser_summary_tests
