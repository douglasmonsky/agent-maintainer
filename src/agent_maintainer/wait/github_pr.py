"""Quiet GitHub pull request checks waiter."""

from __future__ import annotations

import json
import subprocess  # nosec B404
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Final

from agent_maintainer.wait.models import (
    TIMEOUT_EXIT_CODE,
    WaitRepairCapsule,
    render_wait_capsule,
)

DEFAULT_INTERVAL_SECONDS: Final = 20
DEFAULT_TIMEOUT_SECONDS: Final = 3600
PASS_BUCKET: Final = "pass"
FAIL_BUCKET: Final = "fail"
SUCCESS_VALUES: Final = frozenset(("success", "skipped", "neutral"))
FAILURE_VALUES: Final = frozenset(
    ("failure", "cancelled", "timed_out", "action_required", "startup_failure"),
)


def _empty_checks() -> tuple[GitHubPrCheck, ...]:
    return ()


def _terminal_bucket(bucket: str) -> bool:
    """Return whether GitHub bucket is terminal."""
    return bucket in {PASS_BUCKET, FAIL_BUCKET, "skipping", "cancel"}


def _terminal_state(state: str, conclusion: str) -> bool:
    """Return whether GitHub state or conclusion is terminal."""
    return (
        state in SUCCESS_VALUES
        or state in FAILURE_VALUES
        or conclusion in SUCCESS_VALUES
        or conclusion in FAILURE_VALUES
    )


@dataclass(frozen=True)
class GitHubPrCheck:
    """One GitHub PR check state."""

    name: str
    state: str
    conclusion: str = ""
    bucket: str = ""
    link: str = ""

    @property
    def completed(self) -> bool:
        """Return whether this check has reached a terminal state."""
        bucket = self.bucket.lower()
        state = self.state.lower()
        conclusion = self.conclusion.lower()
        return _terminal_bucket(bucket) or _terminal_state(state, conclusion)

    @property
    def succeeded(self) -> bool:
        """Return whether this terminal check should pass the PR wait."""
        bucket = self.bucket.lower()
        state = self.state.lower()
        conclusion = self.conclusion.lower()
        return bucket == PASS_BUCKET or state in SUCCESS_VALUES or conclusion in SUCCESS_VALUES


@dataclass(frozen=True)
class GitHubPrChecksState:
    """GitHub PR checks aggregate state."""

    pr_number: str
    checks: tuple[GitHubPrCheck, ...] = _empty_checks()

    @property
    def completed(self) -> bool:
        """Return whether every reported check has reached a terminal state."""
        return bool(self.checks) and all(check.completed for check in self.checks)

    @property
    def succeeded(self) -> bool:
        """Return whether every terminal check succeeded."""
        return self.completed and not self.failed_checks()

    def failed_checks(self) -> tuple[GitHubPrCheck, ...]:
        """Return terminal checks that failed."""
        return tuple(check for check in self.checks if check.completed and not check.succeeded)


@dataclass(frozen=True)
class GitHubPrWaitConfig:
    """Inputs for waiting on one pull request check set."""

    pr_number: str
    repo: str | None = None
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS


@dataclass(frozen=True)
class GitHubPrWaitResult:
    """Final quiet PR checks wait result."""

    pr_number: str
    state: GitHubPrChecksState | None
    timed_out: bool = False
    error: str = ""

    @property
    def exit_code(self) -> int:
        """Return process exit code for this wait result."""
        if self.timed_out:
            return TIMEOUT_EXIT_CODE
        if self.error:
            return 2
        if self.state is None:
            return 1
        return 0 if self.state.succeeded else 1


QueryPrChecks = Callable[[GitHubPrWaitConfig], GitHubPrChecksState]
Sleep = Callable[[int], None]
Monotonic = Callable[[], float]


def wait_for_github_pr_checks(
    config: GitHubPrWaitConfig,
    *,
    query_checks: QueryPrChecks | None = None,
    sleep: Sleep = time.sleep,
    monotonic: Monotonic = time.monotonic,
) -> GitHubPrWaitResult:
    """Wait quietly until GitHub PR checks complete or time out."""
    query = query_checks or query_github_pr_checks
    started = monotonic()
    while True:
        state = query(config)
        if state.completed:
            return GitHubPrWaitResult(pr_number=config.pr_number, state=state)
        if monotonic() - started >= config.timeout_seconds:
            return GitHubPrWaitResult(
                pr_number=config.pr_number,
                state=state,
                timed_out=True,
            )
        sleep(config.interval_seconds)


def query_github_pr_checks(config: GitHubPrWaitConfig) -> GitHubPrChecksState:
    """Query one PR check set using GitHub CLI JSON output."""
    command = _gh_pr_checks_command(config)
    result = subprocess.run(  # nosec B603
        command,
        capture_output=True,
        check=False,
        text=True,
    )
    if not result.stdout.strip():
        if result.returncode:
            raise RuntimeError(result.stderr.strip())
        return GitHubPrChecksState(pr_number=config.pr_number)
    return parse_github_pr_checks_state(config.pr_number, result.stdout)


def parse_github_pr_checks_state(
    pr_number: str,
    raw_json: str,
) -> GitHubPrChecksState:
    """Parse `gh pr checks --json` output."""
    payload = json.loads(raw_json)
    if not isinstance(payload, Sequence) or isinstance(payload, (str, bytes)):
        return GitHubPrChecksState(pr_number=pr_number)
    return GitHubPrChecksState(
        pr_number=pr_number,
        checks=tuple(_parse_check(item) for item in payload if isinstance(item, dict)),
    )


def render_github_pr_wait_text(result: GitHubPrWaitResult) -> str:
    """Render one compact PR checks wait result."""
    run_id = f"PR #{result.pr_number}"
    if result.error:
        return _render_error(result, run_id)
    if result.timed_out:
        return _render_timeout(result, run_id)
    state = result.state
    if state is None:
        return render_wait_capsule(WaitRepairCapsule(result="UNKNOWN", run_id=run_id))
    if state.succeeded:
        return render_wait_capsule(WaitRepairCapsule(result="PASS", run_id=run_id))
    return _render_failure(result.pr_number, run_id, state)


def render_github_pr_wait_json(result: GitHubPrWaitResult) -> str:
    """Render one JSON PR checks wait result."""
    payload: dict[str, object] = {
        "pr_number": result.pr_number,
        "timed_out": result.timed_out,
        "error": result.error,
        "exit_code": result.exit_code,
    }
    if result.state is not None:
        payload["completed"] = result.state.completed
        payload["failed_checks"] = [check.name for check in result.state.failed_checks()]
        payload["checks"] = [
            {
                "name": check.name,
                "state": check.state,
                "conclusion": check.conclusion,
                "bucket": check.bucket,
                "link": check.link,
            }
            for check in result.state.checks
        ]
    return json.dumps(payload, indent=2, sort_keys=True)


def _gh_pr_checks_command(config: GitHubPrWaitConfig) -> list[str]:
    command = [
        "gh",
        "pr",
        "checks",
        config.pr_number,
        "--json",
        "bucket,link,name,state",
    ]
    if config.repo:
        command.extend(("--repo", config.repo))
    return command


def _parse_check(item: dict[str, Any]) -> GitHubPrCheck:
    return GitHubPrCheck(
        name=str(item.get("name", "")),
        state=str(item.get("state", "")),
        conclusion=str(item.get("conclusion", "")),
        bucket=str(item.get("bucket", "")),
        link=str(item.get("link", "")),
    )


def _render_error(result: GitHubPrWaitResult, run_id: str) -> str:
    return render_wait_capsule(
        WaitRepairCapsule(
            result="ERROR",
            run_id=run_id,
            details=(result.error,),
            likely_next_action=f"gh pr checks {result.pr_number}",
        ),
    )


def _render_timeout(result: GitHubPrWaitResult, run_id: str) -> str:
    return render_wait_capsule(
        WaitRepairCapsule(
            result="TIMEOUT",
            run_id=run_id,
            likely_next_action=(f"python -m agent_maintainer wait github-pr {result.pr_number}"),
        ),
    )


def _render_failure(
    pr_number: str,
    run_id: str,
    state: GitHubPrChecksState,
) -> str:
    return render_wait_capsule(
        WaitRepairCapsule(
            result="FAIL",
            run_id=run_id,
            top_repair_facts=_failed_check_lines(state.failed_checks()),
            likely_next_action=f"gh pr checks {pr_number}",
        ),
    )


def _failed_check_lines(failed_checks: tuple[GitHubPrCheck, ...]) -> tuple[str, ...]:
    if not failed_checks:
        return ("GitHub PR checks: no failed checks reported by gh",)
    return tuple(f"GitHub check: {check.name} ({_check_status(check)})" for check in failed_checks)


def _check_status(check: GitHubPrCheck) -> str:
    return check.conclusion or check.state or check.bucket or "unknown"
