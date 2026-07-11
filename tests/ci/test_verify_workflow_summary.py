"""Tests verify workflow publishes the generated PR summary."""

from __future__ import annotations

from pathlib import Path


def test_verify_workflow_appends_pr_summary_to_step_summary() -> None:
    """GitHub Actions verify workflow appends bounded summary artifact."""

    workflow = Path(".github/workflows/verify.yml").read_text(encoding="utf-8")

    assert "Append verification summary" in workflow
    assert ".verify-logs/pr-summary.md" in workflow
    assert 'cat .verify-logs/pr-summary.md >> "$GITHUB_STEP_SUMMARY"' in workflow
    assert "  verify:\n    name: verify\n" in workflow
