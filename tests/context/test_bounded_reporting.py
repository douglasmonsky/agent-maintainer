"""Tests bounded failure output helpers."""

from __future__ import annotations

from agent_maintainer.core import reporting

SUMMARY_CHAR_LIMIT = 40
SUMMARY_LINE_LIMIT = 2


def test_compact_output_reports_omitted_line_and_char_counts() -> None:
    """Large summaries state how much output was omitted."""

    summary = reporting.compact_output(
        "alpha\nbravo\ncharlie\ndelta",
        max_lines=SUMMARY_LINE_LIMIT,
        max_chars=SUMMARY_CHAR_LIMIT,
    )

    assert "alpha" in summary
    assert "bravo" in summary
    assert "omitted" in summary
    assert "chars" in summary
    assert "lines" in summary
    assert ".verify-logs/" in summary
