"""Tests quiet GitHub PR checks wait behavior."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Iterator

import pytest

from agent_maintainer.wait import github_pr
from agent_maintainer.wait.github_pr import (
    GitHubPrCheck,
    GitHubPrChecksState,
    GitHubPrWaitConfig,
    GitHubPrWaitResult,
    parse_github_pr_checks_state,
    query_github_pr_checks,
    render_github_pr_wait_json,
    render_github_pr_wait_text,
    wait_for_github_pr_checks,
)
from agent_maintainer.wait.models import TIMEOUT_EXIT_CODE

FIRST_TICK = 0.0
SECOND_TICK = 1.0
FINAL_TICK = 4.0


def test_wait_for_github_pr_checks_polls_until_completion() -> None:
    """Waiter polls PR checks until final state without intermediate output."""
    states = QuerySequence(
        iter(
            (
                GitHubPrChecksState(
                    pr_number="291",
                    checks=(GitHubPrCheck(name="verify", state="in_progress"),),
                ),
                GitHubPrChecksState(
                    pr_number="291",
                    checks=(GitHubPrCheck(name="verify", state="success"),),
                ),
            ),
        ),
    )

    result = wait_for_github_pr_checks(
        GitHubPrWaitConfig(pr_number="291", interval_seconds=1),
        query_checks=states,
        sleep=lambda _seconds: None,
    )

    assert result.exit_code == 0
    assert result.state is not None
    assert result.state.succeeded


def test_parse_github_pr_checks_state_reads_failures() -> None:
    """GitHub check JSON becomes compact failure facts."""
    state = parse_github_pr_checks_state(
        "291",
        json.dumps(
            [
                None,
                {
                    "name": "verify",
                    "state": "failure",
                    "conclusion": "failure",
                    "bucket": "fail",
                    "link": "https://check",
                },
                {
                    "name": "docs",
                    "state": "success",
                    "conclusion": "success",
                    "bucket": "pass",
                },
            ],
        ),
    )

    assert state.completed
    assert not state.succeeded
    assert [check.name for check in state.failed_checks()] == ["verify"]


def test_query_github_pr_checks_uses_supported_json_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Query avoids `gh pr checks` fields unavailable in older GitHub CLI."""
    seen_command: list[str] = []

    def fake_run(
        command: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        seen_command.extend(command)
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps([{"name": "verify", "state": "success", "bucket": "pass"}]),
            stderr="",
        )

    monkeypatch.setattr(github_pr.subprocess, "run", fake_run)

    state = query_github_pr_checks(GitHubPrWaitConfig(pr_number="292"))

    assert state.succeeded
    assert "bucket,link,name,state" in seen_command


def test_github_pr_failure_renders_repair_capsule() -> None:
    """Failed PR checks render final repair capsule, not raw polling output."""
    result = GitHubPrWaitResult(
        pr_number="291",
        state=GitHubPrChecksState(
            pr_number="291",
            checks=(
                GitHubPrCheck(
                    name="verify",
                    state="failure",
                    conclusion="failure",
                    bucket="fail",
                ),
            ),
        ),
    )

    text = render_github_pr_wait_text(result)

    assert text.startswith("Result: FAIL\nRun ID: PR #291")
    assert "Top repair facts:\n1. GitHub check: verify (failure)" in text
    assert "Likely next action:\ngh pr checks 291" in text
    assert "Refreshing" not in text


def test_wait_for_github_pr_checks_times_out() -> None:
    """Timeouts exit 124 with rerun command."""
    ticks = iter((FIRST_TICK, SECOND_TICK, FINAL_TICK))
    result = wait_for_github_pr_checks(
        GitHubPrWaitConfig(pr_number="291", interval_seconds=1, timeout_seconds=3),
        query_checks=lambda _config: GitHubPrChecksState(
            pr_number="291",
            checks=(GitHubPrCheck(name="verify", state="in_progress"),),
        ),
        sleep=lambda _seconds: None,
        monotonic=lambda: next(ticks),
    )

    assert result.exit_code == TIMEOUT_EXIT_CODE
    assert "Result: TIMEOUT" in render_github_pr_wait_text(result)
    assert "python -m agent_maintainer wait github-pr 291" in render_github_pr_wait_text(
        result,
    )


def test_github_pr_json_reports_failed_checks() -> None:
    """JSON output exposes compact machine-readable PR check state."""
    result = GitHubPrWaitResult(
        pr_number="291",
        state=GitHubPrChecksState(
            pr_number="291",
            checks=(
                GitHubPrCheck(
                    name="verify",
                    state="failure",
                    conclusion="failure",
                    bucket="fail",
                ),
            ),
        ),
    )

    payload = json.loads(render_github_pr_wait_json(result))

    assert payload["exit_code"] == 1
    assert payload["failed_checks"] == ["verify"]


class QuerySequence:
    """Callable query over predefined PR check states."""

    def __init__(self, states: Iterator[GitHubPrChecksState]) -> None:
        self._states = states

    def __call__(self, _config: GitHubPrWaitConfig) -> GitHubPrChecksState:
        return next(self._states)
