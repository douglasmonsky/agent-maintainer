"""Tests Codex rewake integration in wait CLI."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pytest

from agent_maintainer.wait import cli
from agent_maintainer.wait.codex_rewake import REWAKE_STATUS_RESUMED, CodexRewakeResult
from agent_maintainer.wait.github_pr import (
    GitHubPrCheck,
    GitHubPrChecksState,
    GitHubPrWaitResult,
)
from agent_maintainer.wait.registry import RegisterGitHubPrWait, WaitRecord, WaitRegistry

PR_NUMBER = "291"
SeenWaits = list[str]


def test_sweep_watch_cli_prints_rewake(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Wait sweep watch CLI renders rewake result when backend resumes."""

    SuccessfulRewakeBackend.seen_waits = []
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
    monkeypatch.setattr(cli, "watch_wait", lambda _registry, _wait_id: completed)
    monkeypatch.setattr(cli, "CodexRewakeBackend", SuccessfulRewakeBackend)

    status = cli.main(["sweep", "--watch", record.wait_id, "--root", str(tmp_path)])

    output = capsys.readouterr().out
    assert status == 0
    assert "Result: RESUMED" in output
    assert SuccessfulRewakeBackend.seen_waits == [record.wait_id]


class SuccessfulRewakeBackend:
    """Fake Codex rewake backend for CLI integration coverage."""

    seen_waits: ClassVar[SeenWaits] = []

    def __init__(self, registry: WaitRegistry) -> None:
        self.registry = registry

    def resume_if_available(self, record: WaitRecord) -> CodexRewakeResult:
        self.seen_waits.append(record.wait_id)
        self.seen_count()
        return CodexRewakeResult(
            REWAKE_STATUS_RESUMED,
            "Codex continuation completed",
        )

    def seen_count(self) -> int:
        """Return count of fake rewake calls."""

        return len(self.seen_waits)
