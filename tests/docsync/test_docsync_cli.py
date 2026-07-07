"""Tests for the DocSync CLI."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from docsync import cli as docsync_cli
from docsync.config.defaults import DEFAULT_CONFIG_TEXT
from docsync.config.load import load_config


def test_module_help_exits_success(capsys: pytest.CaptureFixture[str]) -> None:
    """Render top-level DocSync help."""
    with pytest.raises(SystemExit) as exc_info:
        docsync_cli.main(["--help"])

    assert exc_info.value.code == 0
    assert "Documentation traceability" in capsys.readouterr().out


def test_module_help_lists_standalone_command_surface(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Top-level help keeps the documented standalone command surface visible."""
    expected_commands = (
        "init",
        "index",
        "freshness",
        "check",
        "doctor",
        "prompt",
        "repair-object-end-markers",
        "attest",
        "trace",
    )

    with pytest.raises(SystemExit) as exc_info:
        docsync_cli.main(["--help"])

    assert exc_info.value.code == 0
    output = capsys.readouterr().out
    for command in expected_commands:
        assert command in output


def test_doctor_reports_empty_trace(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Doctor loads repository config and reports an empty trace."""
    (tmp_path / ".docsync").mkdir()
    (tmp_path / ".docsync" / "config.yml").write_text(
        DEFAULT_CONFIG_TEXT,
        encoding="utf-8",
    )
    (tmp_path / ".docsync" / "trace.yml").write_text(
        "version: 1\ndocuments: {}\nobjects: {}\nclaims: {}\nevidence: {}\n",
        encoding="utf-8",
    )

    result = docsync_cli.main(["--repo-root", str(tmp_path), "doctor"])

    assert result == 1
    output = capsys.readouterr().out
    assert "DS000" in output
    assert "empty or incomplete" in output


def test_repo_root_global_option_can_follow_subcommand(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Global repo root option works after a subcommand."""
    (tmp_path / ".docsync").mkdir()
    (tmp_path / ".docsync" / "config.yml").write_text(
        DEFAULT_CONFIG_TEXT,
        encoding="utf-8",
    )
    (tmp_path / ".docsync" / "trace.yml").write_text(
        "version: 1\ndocuments: {}\nobjects: {}\nclaims: {}\nevidence: {}\n",
        encoding="utf-8",
    )

    result = docsync_cli.main(["doctor", "--repo-root", str(tmp_path)])

    assert result == 1
    assert "empty or incomplete" in capsys.readouterr().out


def test_init_writes_docsync_files_and_agents_section(tmp_path: Path) -> None:
    """Init creates DocSync files and repository guidance."""
    result = docsync_cli.main(["--repo-root", str(tmp_path), "init"])

    assert result == 0
    assert (tmp_path / ".docsync" / "config.yml").exists()
    assert (tmp_path / ".docsync" / "trace.yml").exists()
    assert not (tmp_path / "AGENTS.md").exists()

    agents_root = tmp_path / "agents"
    agents_root.mkdir()
    agents_result = docsync_cli.main(["--repo-root", str(agents_root), "init", "--agents"])
    assert agents_result == 0
    assert "## DocSync policy" in (agents_root / "AGENTS.md").read_text(encoding="utf-8")
    config = load_config(tmp_path)
    assert config.object_end_marker == "docsync:object.end"
    assert config.require_object_end_markers


def test_init_refuses_existing_files_without_force(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Init refuses to overwrite existing DocSync files by default."""
    assert docsync_cli.main(["--repo-root", str(tmp_path), "init"]) == 0

    result = docsync_cli.main(["--repo-root", str(tmp_path), "init"])

    assert result == 1
    assert "DocSync file already exists" in capsys.readouterr().out


def test_core_commands_write_artifacts_from_fixture_repo(tmp_path: Path) -> None:
    """Index, check, prompt, and attestation commands write expected artifacts."""
    _write_repo(tmp_path)
    _commit_all(tmp_path)

    index_result = docsync_cli.main(["--repo-root", str(tmp_path), "index"])
    check_result = docsync_cli.main(["--repo-root", str(tmp_path), "check", "--base", "HEAD"])
    prompt_result = docsync_cli.main(["--repo-root", str(tmp_path), "prompt", "--base", "HEAD"])
    attest_result = docsync_cli.main(
        [
            "--repo-root",
            str(tmp_path),
            "attest",
            "claim.demo",
            "--evidence",
            "evidence.demo",
            "--reason",
            "internal_refactor_only",
        ]
    )

    assert index_result == 0
    assert check_result == 0
    assert prompt_result == 0
    assert attest_result == 0
    assert (tmp_path / ".docsync" / "out" / "index.json").exists()
    assert (tmp_path / ".docsync" / "out" / "report.json").exists()
    assert (tmp_path / ".docsync" / "out" / "review-packet.json").exists()
    assert (tmp_path / ".docsync" / "out" / "review-prompt.md").exists()
    assert tuple((tmp_path / ".docsync" / "attestations").glob("*.yml"))


def test_repair_object_end_markers_dry_run_and_write(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Repair command inserts explicit object end markers only with --write."""
    _write_repo(tmp_path)
    readme_path = tmp_path / "README.md"
    readme_path.write_text(
        readme_path.read_text(encoding="utf-8").replace(
            "<!-- docsync:object.end docs.readme.demo -->\n",
            "",
        ),
        encoding="utf-8",
    )

    dry_run = docsync_cli.main(["--repo-root", str(tmp_path), "repair-object-end-markers"])

    assert dry_run == 0
    assert "Would insert 1 DocSync object end marker" in capsys.readouterr().out
    assert "docsync:object.end" not in (tmp_path / "README.md").read_text(encoding="utf-8")

    write_run = docsync_cli.main(
        ["--repo-root", str(tmp_path), "repair-object-end-markers", "--write"],
    )

    assert write_run == 0
    content = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "<!-- docsync:object.end docs.readme.demo -->" in content
    assert docsync_cli.main(["--repo-root", str(tmp_path), "doctor"]) == 0


def test_freshness_writes_generated_metadata(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Freshness command writes passive metadata under .docsync/out."""
    _write_repo(tmp_path)

    result = docsync_cli.main(["--repo-root", str(tmp_path), "freshness"])

    assert result == 0
    output = capsys.readouterr().out
    freshness_path = tmp_path / ".docsync" / "out" / "freshness.json"
    payload = json.loads(freshness_path.read_text(encoding="utf-8"))
    assert "Objects: 1 current, 0 missing" in output
    assert "Evidence: 1 current, 0 missing" in output
    assert payload["version"] == 1
    assert payload["ok"] is True
    assert payload["objects"]["docs.readme.demo"]["status"] == "current"
    assert payload["evidence"]["evidence.demo"]["status"] == "current"


def test_freshness_json_no_write(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Freshness can report JSON without writing generated state."""
    _write_repo(tmp_path)

    result = docsync_cli.main(
        ["--repo-root", str(tmp_path), "freshness", "--no-write", "--format", "json"]
    )

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["objects"] == {"current": 1, "missing": 0}
    assert payload["summary"]["evidence"] == {"current": 1, "missing": 0}
    assert not (tmp_path / ".docsync" / "out" / "freshness.json").exists()


def _write_repo(tmp_path: Path) -> None:
    (tmp_path / ".docsync").mkdir()
    (tmp_path / ".docsync" / "config.yml").write_text(
        DEFAULT_CONFIG_TEXT,
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text(
        """
<!-- docsync:object docs.readme.demo -->
# Demo

<!-- docsync:claim claim.demo -->
Demo claim.
<!-- docsync:claim.end claim.demo -->
<!-- docsync:object.end docs.readme.demo -->
""".lstrip(),
        encoding="utf-8",
    )
    (tmp_path / "src.py").write_text(
        """
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
    marker: claim.demo
    text: Demo claim.
    severity: high
    evidence:
      - evidence.demo
    review:
      acceptable_attestation_reasons:
        - internal_refactor_only
evidence:
  evidence.demo:
    type: code
    anchors:
      - path: src.py
        mode: explicit_region
""".lstrip(),
        encoding="utf-8",
    )


def _commit_all(repo_root: Path) -> None:
    _git(repo_root, "init")
    _git(repo_root, "add", ".")
    _git(
        repo_root,
        "-c",
        "user.name=DocSync Test",
        "-c",
        "user.email=docsync@example.invalid",
        "commit",
        "-m",
        "base",
    )


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(
        ("git", *args),
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
