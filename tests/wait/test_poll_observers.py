"""Tests wait poll observer callbacks."""

from __future__ import annotations

from pathlib import Path

from agent_maintainer.wait.github import (
    GitHubRunState,
    GitHubWaitConfig,
    wait_for_github_run,
)
from agent_maintainer.wait.github_pr import (
    GitHubPrCheck,
    GitHubPrChecksState,
    GitHubPrWaitConfig,
    wait_for_github_pr_checks,
)
from agent_maintainer.wait.verifier import VerifierWaitConfig, wait_for_verifier_run

RUN_PENDING = "in_progress"
RUN_DONE = "completed"
PR_NUMBER = "291"
RUN_ID = "123"
VERIFY_RUN = "run-3"


def test_github_run_reports_poll_observations() -> None:
    """GitHub run waiter reports each poll to optional observer."""

    observations: list[tuple[int, str]] = []
    result = wait_for_github_run(
        GitHubWaitConfig(run_id=RUN_ID, interval_seconds=1),
        query_run=RunSequence(
            (
                GitHubRunState(status=RUN_PENDING, conclusion="", url="https://run"),
                GitHubRunState(status=RUN_DONE, conclusion="success", url="https://run"),
            ),
        ),
        sleep=no_sleep,
        poll_observer=lambda attempt, state: observations.append(
            (attempt, state.status),
        ),
    )

    assert result.exit_code == 0
    assert observations == [(1, RUN_PENDING), (2, RUN_DONE)]


def test_github_pr_reports_poll_observations() -> None:
    """GitHub PR waiter reports each poll to optional observer."""

    observations: list[tuple[int, bool]] = []
    result = wait_for_github_pr_checks(
        GitHubPrWaitConfig(pr_number=PR_NUMBER, interval_seconds=1),
        query_checks=PrSequence(
            (
                GitHubPrChecksState(
                    pr_number=PR_NUMBER,
                    checks=(GitHubPrCheck(name="verify", state=RUN_PENDING),),
                ),
                GitHubPrChecksState(
                    pr_number=PR_NUMBER,
                    checks=(GitHubPrCheck(name="verify", state="success"),),
                ),
            ),
        ),
        sleep=no_sleep,
        poll_observer=lambda attempt, state: observations.append(
            (attempt, state.completed),
        ),
    )

    assert result.exit_code == 0
    assert observations == [(1, False), (2, True)]


def test_verifier_reports_poll_observations(tmp_path: Path) -> None:
    """Verifier waiter reports manifest presence to optional observer."""

    observations: list[tuple[int, bool]] = []
    write_manifest(tmp_path)

    result = wait_for_verifier_run(
        VerifierWaitConfig(run_id=VERIFY_RUN, log_dir=tmp_path),
        poll_observer=lambda attempt, exists: observations.append((attempt, exists)),
    )

    assert result.exit_code == 0
    assert observations == [(1, True)]


class RunSequence:
    """Return GitHub run states in order."""

    def __init__(self, states: tuple[GitHubRunState, ...]) -> None:
        self._states = iter(states)

    def __call__(self, _config: GitHubWaitConfig) -> GitHubRunState:
        """Return next run state."""

        return next(self._states)


class PrSequence:
    """Return GitHub PR states in order."""

    def __init__(self, states: tuple[GitHubPrChecksState, ...]) -> None:
        self._states = iter(states)

    def __call__(self, _config: GitHubPrWaitConfig) -> GitHubPrChecksState:
        """Return next PR state."""

        return next(self._states)


def no_sleep(_seconds: int) -> None:
    """Avoid sleeping in tests."""


def write_manifest(log_dir: Path) -> None:
    """Write a minimal passing verifier manifest."""

    run_dir = log_dir / "runs" / VERIFY_RUN
    run_dir.mkdir(parents=True)
    run_dir.joinpath("manifest.json").write_text(
        ('{"profile":"fast","run_id":"run-3","checks":[{"name":"ruff","status":"passed"}]}'),
        encoding="utf-8",
    )
