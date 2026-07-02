"""Tests for DocSync structural validation."""

from __future__ import annotations

from pathlib import Path

from docsync.api import CheckOptions, doctor_repo
from docsync.config.defaults import DEFAULT_CONFIG_TEXT


def test_doctor_passes_minimal_valid_trace(tmp_path: Path) -> None:
    """A minimal connected trace passes structural validation."""
    (tmp_path / ".docsync").mkdir()
    (tmp_path / ".docsync" / "config.yml").write_text(
        DEFAULT_CONFIG_TEXT,
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text(
        """
<!-- docsync:object docs.readme.demo -->
# Demo

<!-- docsync:evidence.start evidence.demo -->
Demo behavior.
<!-- docsync:evidence.end evidence.demo -->
""".lstrip(),
        encoding="utf-8",
    )
    (tmp_path / ".docsync" / "trace.yml").write_text(
        """
version: 1
documents:
  docs.readme:
    path: README.md
    title: Demo
    audience: users
objects:
  docs.readme.demo:
    document: docs.readme
    kind: heading_section
    path: README.md
    marker: docs.readme.demo
    heading:
      level: 1
      text: Demo
claims:
  claim.demo:
    object: docs.readme.demo
    text: Demo claim.
    severity: medium
    evidence:
      - evidence.demo
evidence:
  evidence.demo:
    type: code
    description: Demo evidence.
    anchors:
      - path: README.md
        mode: explicit_region
""".lstrip(),
        encoding="utf-8",
    )

    result = doctor_repo(CheckOptions(repo_root=tmp_path))

    assert result.ok


def test_doctor_reports_missing_claim_evidence(tmp_path: Path) -> None:
    """Claims must point to existing evidence IDs."""
    (tmp_path / ".docsync").mkdir()
    (tmp_path / ".docsync" / "config.yml").write_text(
        DEFAULT_CONFIG_TEXT,
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text(
        """
<!-- docsync:object docs.readme.demo -->
# Demo
""".lstrip(),
        encoding="utf-8",
    )
    (tmp_path / ".docsync" / "trace.yml").write_text(
        """
version: 1
documents:
  docs.readme:
    path: README.md
objects:
  docs.readme.demo:
    document: docs.readme
    kind: heading_section
    path: README.md
    marker: docs.readme.demo
claims:
  claim.demo:
    object: docs.readme.demo
    text: Demo claim.
    severity: medium
    evidence:
      - evidence.missing
evidence: {}
""".lstrip(),
        encoding="utf-8",
    )

    result = doctor_repo(CheckOptions(repo_root=tmp_path))

    assert not result.ok
    assert [finding.code for finding in result.findings] == ["DS204"]


def test_doctor_reports_trace_schema_shape_error(tmp_path: Path) -> None:
    """Trace files must include required top-level mappings."""
    _write_config(tmp_path)
    _write_trace(
        tmp_path,
        """
version: 1
documents: {}
objects: {}
claims: {}
""",
    )

    result = doctor_repo(CheckOptions(repo_root=tmp_path))

    assert [finding.code for finding in result.findings] == ["DS000"]
    assert "missing required top-level" in result.findings[0].message


def test_doctor_reports_missing_markdown_marker(tmp_path: Path) -> None:
    """Trace objects must resolve to hidden Markdown object markers."""
    _write_config(tmp_path)
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    _write_trace(
        tmp_path,
        """
version: 1
documents:
  docs.readme:
    path: README.md
objects:
  docs.readme.demo:
    document: docs.readme
    kind: heading_section
    path: README.md
    marker: docs.readme.demo
claims: {}
evidence: {}
""",
    )

    result = doctor_repo(CheckOptions(repo_root=tmp_path))

    assert [finding.code for finding in result.findings] == ["DS101"]


def test_doctor_reports_title_change(tmp_path: Path) -> None:
    """Heading titles must match trace.yml when configured."""
    _write_config(tmp_path)
    (tmp_path / "README.md").write_text(
        """
<!-- docsync:object docs.readme.demo -->
# Current Demo
""".lstrip(),
        encoding="utf-8",
    )
    _write_trace(
        tmp_path,
        """
version: 1
documents:
  docs.readme:
    path: README.md
objects:
  docs.readme.demo:
    document: docs.readme
    kind: heading_section
    path: README.md
    marker: docs.readme.demo
    heading:
      level: 1
      text: Old Demo
claims: {}
evidence: {}
""",
    )

    result = doctor_repo(CheckOptions(repo_root=tmp_path))

    assert [finding.code for finding in result.findings] == ["DS102"]


def test_doctor_reports_missing_config(tmp_path: Path) -> None:
    """Doctor reports missing DocSync config with fallback locations."""
    result = doctor_repo(CheckOptions(repo_root=tmp_path))

    assert [finding.code for finding in result.findings] == ["DS000"]
    assert "DocSync config not found" in result.findings[0].message


def test_doctor_reports_trace_parse_errors(tmp_path: Path) -> None:
    """Doctor reports invalid trace files with configured trace location."""
    _write_config(tmp_path)
    (tmp_path / ".docsync" / "trace.yml").write_text("[]\n", encoding="utf-8")

    result = doctor_repo(CheckOptions(repo_root=tmp_path))

    assert [finding.code for finding in result.findings] == ["DS000"]
    assert "mapping" in result.findings[0].message


def _write_config(tmp_path: Path) -> None:
    (tmp_path / ".docsync").mkdir()
    (tmp_path / ".docsync" / "config.yml").write_text(
        DEFAULT_CONFIG_TEXT,
        encoding="utf-8",
    )


def _write_trace(tmp_path: Path, content: str) -> None:
    (tmp_path / ".docsync" / "trace.yml").write_text(
        content.lstrip(),
        encoding="utf-8",
    )
