"""Tests for verifier diagnostic artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.models import CheckResult
from agent_maintainer.verify import artifacts

DEFAULT_COVERAGE_FLOOR = 80


def run_context(repo_root: Path) -> artifacts.RunContext:
    """Return a stable verifier run context for artifact tests."""

    return artifacts.RunContext(
        repo_root=repo_root,
        profile="full",
        base_ref="HEAD",
        compare_branch="origin/main",
        staged=False,
        config=MaintainerConfig(),
    )


def test_write_run_artifacts_records_manifest_and_failure_note(tmp_path: Path) -> None:
    log_dir = tmp_path / ".verify-logs"
    result = CheckResult(
        "ruff",
        passed=False,
        output="lint failed",
        command=("ruff", "check"),
        exit_code=1,
        log_path=".verify-logs/ruff.log",
        started_at="2026-06-25T10:00:00Z",
        ended_at="2026-06-25T10:00:01Z",
        artifact_paths=("coverage.xml",),
    )

    artifacts.write_run_artifacts(log_dir, run_context(tmp_path), [result])

    manifest = json.loads((log_dir / artifacts.MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["profile"] == "full"
    assert manifest["base_ref"] == "HEAD"
    assert manifest["thresholds"]["coverage_fail_under"] == DEFAULT_COVERAGE_FLOOR
    assert manifest["checks"] == [
        {
            "name": "ruff",
            "status": "failed",
            "command": ["ruff", "check"],
            "exit_code": 1,
            "log_path": ".verify-logs/ruff.log",
            "log_bytes": 0,
            "summary_chars": len("lint failed"),
            "summary_truncated": False,
            "omitted_chars": 0,
            "omitted_lines": 0,
            "expansion_commands": [
                "python -m agent_maintainer context failures --check ruff --limit 20",
                "python -m agent_maintainer context log ruff --tail 120",
            ],
            "started_at": "2026-06-25T10:00:00Z",
            "ended_at": "2026-06-25T10:00:01Z",
            "artifacts": ["coverage.xml"],
        }
    ]

    failure_note = (log_dir / artifacts.LAST_FAILURE_NAME).read_text(encoding="utf-8")
    pr_summary = (log_dir / artifacts.PR_SUMMARY_NAME).read_text(encoding="utf-8")
    assert "### ruff" in failure_note
    assert "lint failed" in failure_note
    assert "python3 -m agent_maintainer verify --profile full" in failure_note
    assert "## Verification Result" in pr_summary
    assert "## Top Failures" in pr_summary
    assert "## Test Intelligence" in pr_summary
    assert "## Ratchet Targets" in pr_summary
    assert "## Change Budget" in pr_summary
    assert "## Change Plan Status" in pr_summary
    assert "## Context Pack Path" in pr_summary
    assert "## Expansion Commands" in pr_summary
    assert "lint failed" in pr_summary


def test_write_run_artifacts_removes_stale_failure_note_on_success(tmp_path: Path) -> None:
    log_dir = tmp_path / ".verify-logs"
    log_dir.mkdir()
    failure_note = log_dir / artifacts.LAST_FAILURE_NAME
    failure_note.write_text("stale\n", encoding="utf-8")
    result = CheckResult(
        "ruff",
        passed=True,
        command=("ruff", "check"),
        exit_code=0,
        log_path=".verify-logs/ruff.log",
        started_at="2026-06-25T10:00:00Z",
        ended_at="2026-06-25T10:00:01Z",
    )

    artifacts.write_run_artifacts(log_dir, run_context(tmp_path), [result])

    assert not failure_note.exists()
    manifest = json.loads((log_dir / artifacts.MANIFEST_NAME).read_text(encoding="utf-8"))
    pr_summary = (log_dir / artifacts.PR_SUMMARY_NAME).read_text(encoding="utf-8")
    assert manifest["checks"][0]["status"] == "passed"
    assert "Result: **PASS**" in pr_summary
