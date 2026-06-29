"""Tests static HTML report generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_maintainer.report import cli as report_cli
from agent_maintainer.report.html import generate_html_report
from agent_maintainer.verify.artifacts import LAST_FAILURE_NAME, MANIFEST_NAME
from agent_maintainer.verify.pr_summary import PR_SUMMARY_NAME


def test_html_report_renders_sections(tmp_path: Path) -> None:
    """Generate a self-contained report from verifier artifacts."""
    log_dir = tmp_path / ".verify-logs"
    log_dir.mkdir()
    write_report_artifacts(log_dir)

    output = generate_html_report(log_dir)

    assert output == log_dir / "report" / "index.html"
    html = output.read_text(encoding="utf-8")
    expected_fragments = (
        "<h1>Agent Maintainer Verification Report</h1>",
        'id="verification-summary"',
        'id="failed-checks"',
        'id="test-intelligence"',
        'id="ratchet-status"',
        'id="change-plan-status"',
        'id="context-pack-links"',
        'id="coverage"',
        'id="architecture"',
        'id="release-readiness"',
        "lint failed &lt;bad&gt;",
        "../ruff.log",
        "../../coverage.xml",
        "python -m agent_maintainer context log ruff --tail 120",
    )
    missing = [fragment for fragment in expected_fragments if fragment not in html]
    assert not missing
    assert "No external service" not in html


def test_report_cli_writes_custom_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI writes report and prints output path."""
    log_dir = tmp_path / ".verify-logs"
    output = tmp_path / "report.html"
    log_dir.mkdir()
    write_report_artifacts(log_dir)

    status = report_cli.main(["html", "--log-dir", str(log_dir), "--output", str(output)])

    assert status == 0
    assert output.exists()
    assert str(output) in capsys.readouterr().out


def test_generate_html_report_requires_manifest(tmp_path: Path) -> None:
    """Missing manifest gives actionable failure."""
    with pytest.raises(FileNotFoundError, match="run verification first"):
        generate_html_report(tmp_path / ".verify-logs")


def write_report_artifacts(log_dir: Path) -> None:
    """Write minimal verifier artifacts for report tests."""
    manifest = {
        "version": 1,
        "generated_at": "2026-06-29T16:30:00Z",
        "profile": "full",
        "base_ref": "HEAD",
        "compare_branch": "origin/main",
        "thresholds": {"coverage_fail_under": 90},
        "checks": [
            {
                "name": "ruff",
                "status": "failed",
                "log_path": ".verify-logs/ruff.log",
                "artifacts": [],
                "expansion_commands": [
                    "python -m agent_maintainer context log ruff --tail 120",
                ],
            },
            {
                "name": "pytest-coverage",
                "status": "passed",
                "log_path": ".verify-logs/pytest-coverage.log",
                "artifacts": ["coverage.xml"],
                "expansion_commands": [],
            },
            {
                "name": "tach",
                "status": "passed",
                "log_path": ".verify-logs/tach.log",
                "artifacts": [],
                "expansion_commands": [],
            },
            {
                "name": "secret-scan",
                "status": "skipped",
                "log_path": ".verify-logs/secret-scan.log",
                "artifacts": [],
                "expansion_commands": [],
            },
        ],
    }
    (log_dir / MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    (log_dir / PR_SUMMARY_NAME).write_text(
        """
# Agent Maintainer Verification Summary

## Test Intelligence
- Likely tests: tests/test_example.py

## Ratchet Targets
- No ratchet targets.

## Change Plan Status
- Check plans: `python -m agent_maintainer change-plan check`

## Context Pack Path
- Context pack not generated in run.
""".strip(),
        encoding="utf-8",
    )
    (log_dir / LAST_FAILURE_NAME).write_text("lint failed <bad>", encoding="utf-8")
