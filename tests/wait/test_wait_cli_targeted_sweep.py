"""Tests targeted wait sweep CLI behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer.wait import cli
from agent_maintainer.wait.github import GitHubRunState, GitHubWaitResult
from agent_maintainer.wait.github_pr import (
    GitHubPrCheck,
    GitHubPrChecksState,
    GitHubPrWaitResult,
)
from agent_maintainer.wait.registry import (
    RegisterGitHubPrWait,
    RegisterGitHubRunWait,
    WaitRecord,
    WaitRegistry,
)

PR_NUMBER = "291"


def test_sweep_one_cli_stays_silent_for_pending_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Targeted one-shot sweep ignores stale ready waits while target pending."""

    registry = WaitRegistry(tmp_path)
    pending = registry.register_github_pr(
        RegisterGitHubPrWait(root=tmp_path, pr_number=PR_NUMBER),
    )
    stale = registry.register_github_run(
        RegisterGitHubRunWait(root=tmp_path, run_id="123"),
    )
    registry.complete_github_run(
        stale,
        GitHubWaitResult(
            run_id="123",
            state=GitHubRunState(
                status="completed",
                conclusion="success",
                url="https://run",
            ),
        ),
    )
    swept_wait_ids: list[str] = []

    def fake_sweep_record(
        _registry: WaitRegistry,
        record: WaitRecord,
    ) -> WaitRecord:
        swept_wait_ids.append(record.wait_id)
        return record

    monkeypatch.setattr(cli, "sweep_record", fake_sweep_record)

    status = cli.main(["sweep", "--one", pending.wait_id, "--root", str(tmp_path)])

    assert status == 0
    assert swept_wait_ids == [pending.wait_id]
    assert capsys.readouterr().out == ""


def test_sweep_one_cli_prints_ready_target(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Targeted one-shot sweep renders final resume text for ready target."""

    registry = WaitRegistry(tmp_path)
    record = registry.register_github_pr(
        RegisterGitHubPrWait(root=tmp_path, pr_number=PR_NUMBER),
    )
    completed = registry.complete_github_pr(
        record,
        GitHubPrWaitResult(
            pr_number=PR_NUMBER,
            state=GitHubPrChecksState(
                pr_number=PR_NUMBER,
                checks=(GitHubPrCheck(name="verify", state="success"),),
            ),
        ),
    )

    status = cli.main(["sweep", "--one", completed.wait_id, "--root", str(tmp_path)])

    output = capsys.readouterr().out
    assert status == 0
    assert "Result: PASS" in output
    assert "Continuation:" in output
