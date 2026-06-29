"""Tests GitHub PR verification summary rendering."""

from __future__ import annotations

from pathlib import Path

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.models import CheckResult
from agent_maintainer.verify.artifacts import RunContext
from agent_maintainer.verify.pr_summary import render_pr_summary
from agent_maintainer.verify.pr_summary_support import MAX_PR_SUMMARY_CHARS


def test_pr_summary_reports_change_budget_and_context_pack(tmp_path: Path) -> None:
    """PR summary includes phase-required sections and context pack path."""

    log_dir = tmp_path / ".verify-logs"
    pack_path = log_dir / "context" / "PACK.md"
    pack_path.parent.mkdir(parents=True)
    pack_path.write_text("pack\n", encoding="utf-8")
    result = CheckResult(
        "change-budget",
        passed=True,
        warning=True,
        output="WARN: Large Python source diff",
        log_path=".verify-logs/change-budget.log",
    )

    summary = render_pr_summary(
        log_dir=log_dir,
        context=run_context(tmp_path, ratchet_enabled=True),
        results=[result],
    )

    assert "Result: **PASS**" in summary
    assert "change-budget" in summary
    assert "Large Python source diff" in summary
    assert "ratchet next" in summary
    assert ".verify-logs/context/PACK.md" in summary
    assert "change-plan check" in summary


def test_pr_summary_is_bounded(tmp_path: Path) -> None:
    """PR summary respects configured context budget."""

    result = CheckResult(
        "ruff",
        passed=False,
        output="\n".join(f"failure {index}" for index in range(400)),
    )

    summary = render_pr_summary(
        log_dir=tmp_path / ".verify-logs",
        context=run_context(
            tmp_path,
            config=MaintainerConfig(context_last_failure_budget_chars=800),
        ),
        results=[result],
    )

    assert len(summary) < MAX_PR_SUMMARY_CHARS
    assert "PR summary omitted" in summary


def run_context(
    repo_root: Path,
    *,
    config: MaintainerConfig | None = None,
    ratchet_enabled: bool = False,
) -> RunContext:
    """Return stable run context for PR summary tests."""

    active_config = config or MaintainerConfig(ratchet_enabled=ratchet_enabled)
    return RunContext(
        repo_root=repo_root,
        profile="ci",
        base_ref="origin/main",
        compare_branch="origin/main",
        staged=False,
        config=active_config,
        run_id="20260625T100000Z-ci-test",
    )
