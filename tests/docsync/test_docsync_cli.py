"""Tests for the DocSync CLI."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from docsync import cli as docsync_cli
from docsync.config.defaults import DEFAULT_CONFIG_TEXT


def test_module_help_exits_success(capsys: pytest.CaptureFixture[str]) -> None:
    """Render top-level DocSync help."""
    with pytest.raises(SystemExit) as exc_info:
        docsync_cli.main(["--help"])

    assert exc_info.value.code == 0
    assert "Documentation traceability" in capsys.readouterr().out


def test_doctor_reports_empty_trace(capsys: pytest.CaptureFixture[str]) -> None:
    """Doctor loads repository config and reports an empty trace."""
    result = docsync_cli.main(["doctor"])

    assert result == 1
    output = capsys.readouterr().out
    assert "DS000" in output
    assert "empty or incomplete" in output


def test_init_writes_docsync_files_and_agents_section(tmp_path: Path) -> None:
    """Init creates DocSync files and repository guidance."""
    result = docsync_cli.main(["--repo-root", str(tmp_path), "init"])

    assert result == 0
    assert (tmp_path / ".docsync" / "config.yml").exists()
    assert (tmp_path / ".docsync" / "trace.yml").exists()
    assert "## DocSync policy" in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")


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

Demo claim.
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
