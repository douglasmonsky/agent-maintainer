"""Quiet GitHub Actions run waiter."""

from __future__ import annotations

import json
import subprocess  # nosec B404
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Final

from agent_waits.models import (
    TIMEOUT_EXIT_CODE,
    WaitRepairCapsule,
    render_wait_capsule,
)

COMPLETED = "completed"
SUCCESS = "success"
DEFAULT_INTERVAL_SECONDS: Final = 20
DEFAULT_TIMEOUT_SECONDS: Final = 3600


def _empty_jobs() -> tuple[GitHubJob, ...]:
    return ()


@dataclass(frozen=True)
class GitHubJob:
    """One GitHub Actions job state."""

    name: str
    status: str
    conclusion: str
    url: str = ""


@dataclass(frozen=True)
class GitHubRunState:
    """GitHub Actions run state returned by `gh run view`."""

    status: str
    conclusion: str
    url: str
    jobs: tuple[GitHubJob, ...] = field(default_factory=_empty_jobs)

    @property
    def completed(self) -> bool:
        """Return whether the run reached a final state."""
        return self.status == COMPLETED

    @property
    def succeeded(self) -> bool:
        """Return whether the run completed successfully."""
        return self.completed and self.conclusion == SUCCESS

    def failed_jobs(self) -> tuple[GitHubJob, ...]:
        """Return completed jobs with non-success conclusions."""
        return tuple(
            job
            for job in self.jobs
            if job.status == COMPLETED and job.conclusion not in {"", SUCCESS, "skipped"}
        )


@dataclass(frozen=True)
class GitHubWaitConfig:
    """Inputs for waiting on one GitHub Actions run."""

    run_id: str
    repo: str | None = None
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS


@dataclass(frozen=True)
class GitHubWaitResult:
    """Final quiet wait result."""

    run_id: str
    state: GitHubRunState | None
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


QueryRun = Callable[[GitHubWaitConfig], GitHubRunState]
Sleep = Callable[[int], None]
Monotonic = Callable[[], float]
GitHubPollObserver = Callable[[int, GitHubRunState], None]


def wait_for_github_run(
    config: GitHubWaitConfig,
    *,
    query_run: QueryRun | None = None,
    sleep: Sleep = time.sleep,
    monotonic: Monotonic = time.monotonic,
    poll_observer: GitHubPollObserver | None = None,
) -> GitHubWaitResult:
    """Wait quietly until a GitHub Actions run completes or times out."""
    query = query_run or query_github_run
    started = monotonic()
    attempt = 0
    while True:
        attempt += 1
        state = query(config)
        if poll_observer is not None:
            poll_observer(attempt, state)
        if state.completed:
            return GitHubWaitResult(run_id=config.run_id, state=state)
        if monotonic() - started >= config.timeout_seconds:
            return GitHubWaitResult(run_id=config.run_id, state=state, timed_out=True)
        sleep(config.interval_seconds)


def query_github_run(config: GitHubWaitConfig) -> GitHubRunState:
    """Query one GitHub Actions run using GitHub CLI JSON output."""
    command = _gh_run_view_command(config)
    result = subprocess.run(  # nosec B603
        command,
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return parse_github_run_state(result.stdout)


def parse_github_run_state(raw_json: str) -> GitHubRunState:
    """Parse `gh run view --json` output."""
    payload = json.loads(raw_json)
    return GitHubRunState(
        status=str(payload.get("status", "")),
        conclusion=str(payload.get("conclusion", "")),
        url=str(payload.get("url", "")),
        jobs=_parse_jobs(payload.get("jobs", ())),
    )


def render_github_wait_text(result: GitHubWaitResult) -> str:
    """Render one compact wait result."""
    if result.error:
        return _render_error(result)
    if result.timed_out:
        return _render_timeout(result)
    state = result.state
    if state is None:
        return render_wait_capsule(
            WaitRepairCapsule(result="UNKNOWN", run_id=result.run_id),
        )
    if state.succeeded:
        return render_wait_capsule(
            WaitRepairCapsule(
                result="PASS",
                run_id=result.run_id,
                expand_command=state.url,
            ),
        )
    return _render_failure(result.run_id, state)


def render_github_wait_json(result: GitHubWaitResult) -> str:
    """Render one JSON wait result."""
    payload: dict[str, object] = {
        "run_id": result.run_id,
        "timed_out": result.timed_out,
        "error": result.error,
        "exit_code": result.exit_code,
    }
    if result.state is not None:
        payload["status"] = result.state.status
        payload["conclusion"] = result.state.conclusion
        payload["url"] = result.state.url
        payload["failed_jobs"] = [job.name for job in result.state.failed_jobs()]
    return json.dumps(payload, indent=2, sort_keys=True)


def _gh_run_view_command(config: GitHubWaitConfig) -> list[str]:
    command = [
        "gh",
        "run",
        "view",
        config.run_id,
        "--json",
        "status,conclusion,url,jobs",
    ]
    if config.repo:
        command.extend(("--repo", config.repo))
    return command


def _parse_jobs(raw_jobs: object) -> tuple[GitHubJob, ...]:
    if not isinstance(raw_jobs, Sequence) or isinstance(raw_jobs, (str, bytes)):
        return ()
    return tuple(_parse_job(job) for job in raw_jobs if isinstance(job, dict))


def _parse_job(job: dict[str, Any]) -> GitHubJob:
    return GitHubJob(
        name=str(job.get("name", "")),
        status=str(job.get("status", "")),
        conclusion=str(job.get("conclusion", "")),
        url=str(job.get("url", "")),
    )


def _render_error(result: GitHubWaitResult) -> str:
    return render_wait_capsule(
        WaitRepairCapsule(
            result="ERROR",
            run_id=result.run_id,
            details=(result.error,),
            likely_next_action=f"gh run view {result.run_id}",
        ),
    )


def _render_timeout(result: GitHubWaitResult) -> str:
    return render_wait_capsule(
        WaitRepairCapsule(
            result="TIMEOUT",
            run_id=result.run_id,
            likely_next_action=(f"python -m agent_maintainer wait github-run {result.run_id}"),
        ),
    )


def _render_failure(run_id: str, state: GitHubRunState) -> str:
    return render_wait_capsule(
        WaitRepairCapsule(
            result="FAIL",
            run_id=run_id,
            details=(f"Conclusion: {state.conclusion}",),
            top_repair_facts=_failed_job_lines(state.failed_jobs()),
            likely_next_action=f"gh run view {run_id} --log-failed",
            expand_command=state.url,
        ),
    )


def _failed_job_lines(failed_jobs: tuple[GitHubJob, ...]) -> tuple[str, ...]:
    if not failed_jobs:
        return ("GitHub: no failed jobs reported by gh",)
    return tuple(f"GitHub job: {job.name} ({job.conclusion})" for job in failed_jobs)
