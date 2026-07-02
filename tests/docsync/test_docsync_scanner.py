"""Tests for DocSync evidence scanning."""

from __future__ import annotations

from pathlib import Path

from docsync.comments.scanner import scan_evidence_file


def test_scanner_rejects_mismatched_region_id(tmp_path: Path) -> None:
    """Start and end evidence IDs must match."""
    path = tmp_path / "sample.py"
    path.write_text(
        """
# docsync:evidence.start evidence.one
value = 1
# docsync:evidence.end evidence.two
""".lstrip(),
        encoding="utf-8",
    )

    result = scan_evidence_file(
        tmp_path,
        Path("sample.py"),
        start_directive="docsync:evidence.start",
        end_directive="docsync:evidence.end",
    )

    assert [finding.code for finding in result.findings] == ["DS003"]


def test_scanner_rejects_empty_region(tmp_path: Path) -> None:
    """Evidence regions must contain at least one content line."""
    path = tmp_path / "sample.py"
    path.write_text(
        """
# docsync:evidence.start evidence.one
# docsync:evidence.end evidence.one
""".lstrip(),
        encoding="utf-8",
    )

    result = scan_evidence_file(
        tmp_path,
        Path("sample.py"),
        start_directive="docsync:evidence.start",
        end_directive="docsync:evidence.end",
    )

    assert [finding.code for finding in result.findings] == ["DS008"]
