"""Tests quiet GitHub Actions wait behavior."""

from __future__ import annotations

import json
from collections.abc import Iterator

from agent_maintainer.wait.github import (
    TIMEOUT_EXIT_CODE,
    GitHubRunState,
    GitHubWaitConfig,
    GitHubWaitResult,
    parse_github_run_state,
    render_github_wait_json,
    render_github_wait_text,
    wait_for_github_run,
)

FIRST_TICK = 0
SECOND_TICK = 2.0
FINAL_TICK = 4.0


def test_github_run_wait_returns_success() -> None:
    """Waiter polls until completion and returns final state only."""
    states = iter(
        (
            GitHubRunState(status="in_progress", conclusion="", url="https://run"),
            GitHubRunState(status="completed", conclusion="success", url="https://run"),
        ),
    )
    sleeps: list[int] = []

    result = wait_for_github_run(
        GitHubWaitConfig(run_id="123", interval_seconds=7),
        query_run=QuerySequence(states),
        sleep=sleeps.append,
    )

    assert result.exit_code == 0
    assert sleeps == [7]
    assert render_github_wait_text(result) == (
        "Result: PASS\nRun ID: 123\n\nExpand only if needed:\nhttps://run"
    )


def test_failure_capsule_lists_failed_jobs() -> None:
    """Failed run output is summary-first with one next command."""
    state = parse_github_run_state(
        json.dumps(
            {
                "status": "completed",
                "conclusion": "failure",
                "url": "https://run",
                "jobs": [
                    {
                        "name": "verify",
                        "status": "completed",
                        "conclusion": "failure",
                        "url": "https://job",
                    },
                    {
                        "name": "compatibility",
                        "status": "completed",
                        "conclusion": "success",
                    },
                ],
            },
        ),
    )

    text = render_github_wait_text(GitHubWaitResult(run_id="123", state=state))

    assert text.startswith("Result: FAIL\nRun ID: 123")
    assert "Top repair facts:\n1. GitHub job: verify (failure)" in text
    assert "Likely next action:\ngh run view 123 --log-failed" in text
    assert "Expand only if needed:\nhttps://run" in text


def test_wait_for_github_run_times_out() -> None:
    """Timeouts exit with 124 and a rerun command."""
    ticks = iter((FIRST_TICK, SECOND_TICK, FINAL_TICK))

    result = wait_for_github_run(
        GitHubWaitConfig(run_id="123", interval_seconds=1, timeout_seconds=3),
        query_run=lambda _config: GitHubRunState(
            status="in_progress",
            conclusion="",
            url="https://run",
        ),
        sleep=lambda _seconds: None,
        monotonic=lambda: next(ticks),
    )

    assert result.exit_code == TIMEOUT_EXIT_CODE
    assert "Result: TIMEOUT" in render_github_wait_text(result)


def test_wait_json_includes_failed_jobs() -> None:
    """JSON output exposes compact machine-readable final state."""
    result = GitHubWaitResult(
        run_id="123",
        state=GitHubRunState(
            status="completed",
            conclusion="failure",
            url="https://run",
            jobs=(
                parse_github_run_state(
                    json.dumps(
                        {
                            "status": "completed",
                            "conclusion": "failure",
                            "url": "https://run",
                            "jobs": [
                                {
                                    "name": "verify",
                                    "status": "completed",
                                    "conclusion": "failure",
                                },
                            ],
                        },
                    ),
                ).jobs[0],
            ),
        ),
    )

    payload = json.loads(render_github_wait_json(result))

    assert payload["exit_code"] == 1
    assert payload["failed_jobs"] == ["verify"]


class QuerySequence:
    """Callable query helper returning predefined run states."""

    def __init__(self, states: Iterator[GitHubRunState]) -> None:
        self._states = states

    def __call__(self, _config: GitHubWaitConfig) -> GitHubRunState:
        return next(self._states)
