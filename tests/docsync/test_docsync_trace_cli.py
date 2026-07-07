"""Tests for DocSync trace authoring CLI commands."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from docsync import cli as docsync_cli
from docsync.config.defaults import DEFAULT_CONFIG_TEXT


def test_trace_authoring_commands_update_trace_and_markers(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Trace authoring commands create entries and optional source markers."""
    _write_empty_trace_repo(tmp_path)
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    (tmp_path / "src.py").write_text("Demo behavior.\n", encoding="utf-8")

    assert (
        docsync_cli.main(
            [
                "trace",
                "--repo-root",
                str(tmp_path),
                "add-document",
                "docs.readme",
                "--path",
                "README.md",
                "--title",
                "Demo Guide",
                "--audience",
                "maintainers",
            ]
        )
        == 0
    )
    assert (
        docsync_cli.main(
            [
                "--repo-root",
                str(tmp_path),
                "trace",
                "add-object",
                "docs.readme.demo",
                "--document",
                "docs.readme",
                "--path",
                "README.md",
                "--marker",
                "docs.readme.demo",
                "--heading-level",
                "1",
                "--heading-text",
                "Demo",
                "--insert-marker",
            ]
        )
        == 0
    )
    assert (
        docsync_cli.main(
            [
                "--repo-root",
                str(tmp_path),
                "trace",
                "add-evidence",
                "evidence.demo",
                "--path",
                "src.py",
                "--type",
                "code",
                "--description",
                "Demo behavior",
                "--insert-region",
            ]
        )
        == 0
    )
    assert (
        docsync_cli.main(
            [
                "--repo-root",
                str(tmp_path),
                "trace",
                "add-claim",
                "claim.demo",
                "--object",
                "docs.readme.demo",
                "--text",
                "Demo claim.",
                "--severity",
                "high",
                "--evidence",
                "evidence.demo",
            ]
        )
        == 0
    )

    capsys.readouterr()
    assert docsync_cli.main(["--repo-root", str(tmp_path), "trace", "list"]) == 0
    output = capsys.readouterr().out
    assert "docs.readme" in output
    assert "docs.readme.demo" in output
    assert "claim.demo" in output
    assert "evidence.demo" in output

    trace_text = (tmp_path / ".docsync" / "trace.yml").read_text(encoding="utf-8")
    payload = yaml.safe_load(trace_text)
    assert payload["documents"]["docs.readme"]["title"] == "Demo Guide"
    assert payload["objects"]["docs.readme.demo"]["heading"] == {
        "level": 1,
        "text": "Demo",
    }
    assert payload["claims"]["claim.demo"]["evidence"] == ["evidence.demo"]
    assert payload["evidence"]["evidence.demo"]["anchors"] == [
        {"path": "src.py", "mode": "explicit_region"}
    ]
    assert trace_text.index("documents:") < trace_text.index("objects:")
    assert trace_text.index("objects:") < trace_text.index("claims:")
    assert trace_text.index("claims:") < trace_text.index("evidence:")
    assert "<!-- docsync:object docs.readme.demo -->" in (tmp_path / "README.md").read_text(
        encoding="utf-8"
    )
    assert "<!-- docsync:evidence.start evidence.demo -->" in (tmp_path / "src.py").read_text(
        encoding="utf-8"
    )


def test_trace_authoring_refuses_overwrite_without_force(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Trace authoring refuses to overwrite IDs unless forced."""
    _write_empty_trace_repo(tmp_path)
    command = [
        "--repo-root",
        str(tmp_path),
        "trace",
        "add-document",
        "docs.readme",
        "--path",
        "README.md",
        "--title",
        "Demo Guide",
        "--audience",
        "maintainers",
    ]

    assert docsync_cli.main(command) == 0
    assert docsync_cli.main(command) == 1
    assert "already exists" in capsys.readouterr().out
    assert docsync_cli.main([*command, "--force", "--title", "Updated Guide"]) == 0

    payload = yaml.safe_load((tmp_path / ".docsync" / "trace.yml").read_text())
    assert payload["documents"]["docs.readme"]["title"] == "Updated Guide"


def test_doctor_fix_creates_starter_dirs_and_repairs_markers(tmp_path: Path) -> None:
    """Doctor --fix applies safe starter repairs before validation."""
    _write_empty_trace_repo(tmp_path)
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
    heading:
      level: 1
      text: Demo
claims: {}
evidence: {}
""".lstrip(),
        encoding="utf-8",
    )

    result = docsync_cli.main(["--repo-root", str(tmp_path), "doctor", "--fix"])

    assert result == 0
    assert (tmp_path / ".docsync" / "attestations" / ".gitkeep").exists()
    assert (tmp_path / ".docsync" / "out" / ".gitignore").exists()
    assert "<!-- docsync:object.end docs.readme.demo -->" in (tmp_path / "README.md").read_text(
        encoding="utf-8"
    )


def _write_empty_trace_repo(tmp_path: Path) -> None:
    (tmp_path / ".docsync").mkdir()
    (tmp_path / ".docsync" / "config.yml").write_text(
        DEFAULT_CONFIG_TEXT,
        encoding="utf-8",
    )
    (tmp_path / ".docsync" / "trace.yml").write_text(
        "version: 1\ndocuments: {}\nobjects: {}\nclaims: {}\nevidence: {}\n",
        encoding="utf-8",
    )
