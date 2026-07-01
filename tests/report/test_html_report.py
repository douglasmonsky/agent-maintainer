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
    """Generate self-contained report verifier artifacts."""
    log_dir = tmp_path / ".verify-logs"
    log_dir.mkdir()
    write_report_artifacts(log_dir)

    output = generate_html_report(log_dir)

    assert output == log_dir / "report" / "index.html"
    html = output.read_text(encoding="utf-8")
    expected_fragments = (
        "<h1>Agent Maintainer Verification Report</h1>",
        'id="verification-summary"',
        'id="technical-debt-score"',
        'id="failed-checks"',
        'id="test-intelligence"',
        'id="ratchet-status"',
        'id="change-plan-status"',
        'id="context-pack-links"',
        'id="coverage"',
        'id="architecture"',
        'id="release-readiness"',
        "lint failed &lt;bad&gt;",
        "Technical Debt Score",
        "23/100",
        "watch items",
        "Watch item.",
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


def test_html_report_handles_missing_debt_score(tmp_path: Path) -> None:
    """Report gives the assess command when debt score was not run."""

    log_dir = tmp_path / ".verify-logs"
    log_dir.mkdir()
    write_report_artifacts(log_dir)
    (log_dir / "technical-debt-score.json").unlink()

    output = generate_html_report(log_dir)
    html = output.read_text(encoding="utf-8")

    assert "No Technical Debt Score artifact found" in html
    assert "python -m agent_maintainer assess debt" in html


def test_html_report_handles_invalid_debt_score(tmp_path: Path) -> None:
    """Report handles a malformed score artifact without failing."""

    log_dir = tmp_path / ".verify-logs"
    log_dir.mkdir()
    write_report_artifacts(log_dir)
    (log_dir / "technical-debt-score.json").write_text("{bad", encoding="utf-8")

    output = generate_html_report(log_dir)
    html = output.read_text(encoding="utf-8")

    assert "Technical Debt Score artifact is not valid JSON" in html


def write_report_artifacts(log_dir: Path) -> None:
    """Write minimal verifier artifacts."""
    manifest = {
        "profile": "full",
        "base_ref": "HEAD",
        "compare_branch": "origin/main",
        "generated_at": "2026-06-30T00:00:00Z",
        "thresholds": {"coverage": 90},
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
                "status": "skipped-disabled",
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
    (log_dir / "technical-debt-score.json").write_text(
        json.dumps(
            {
                "score": 23,
                "risk": "low",
                "confidence": "high",
                "interpretation": "Healthy overall; treat listed categories as watch items.",
                "categories": [
                    {
                        "name": "Reviewability",
                        "score": 30,
                        "status": "moderate",
                        "interpretation": "Watch item.",
                    },
                ],
            },
        ),
        encoding="utf-8",
    )
