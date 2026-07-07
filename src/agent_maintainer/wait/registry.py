"""Agent Maintainer wait registry adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final

from agent_maintainer.wait.github_pr import (
    GitHubPrCheck,
    GitHubPrChecksState,
    GitHubPrWaitResult,
    render_github_pr_wait_text,
)
from agent_waits import registry as wait_registry
from agent_waits.registry import RegisterWait, WaitRecord
from agent_waits.registry import WaitRegistry as BaseWaitRegistry

WAIT_KIND_GITHUB_PR: Final = "github-pr"
RESULT_ERROR = wait_registry.RESULT_ERROR
RESULT_FAIL = wait_registry.RESULT_FAIL
RESULT_PASS = wait_registry.RESULT_PASS
RESULT_PENDING = wait_registry.RESULT_PENDING
RESULT_TIMEOUT = wait_registry.RESULT_TIMEOUT
RESULT_UNKNOWN = wait_registry.RESULT_UNKNOWN
SCHEMA_VERSION = wait_registry.SCHEMA_VERSION
WAIT_STATUS_PENDING = wait_registry.WAIT_STATUS_PENDING
WAIT_STATUS_READY = wait_registry.WAIT_STATUS_READY
WAIT_STATUS_RESUMED = wait_registry.WAIT_STATUS_RESUMED
WAITS_DIR = wait_registry.WAITS_DIR
WaitRegistryError = wait_registry.WaitRegistryError
render_resume_text = wait_registry.render_resume_text
render_wait_record_text = wait_registry.render_wait_record_text
wait_record_from_dict = wait_registry.wait_record_from_dict
wait_record_json = wait_registry.wait_record_json
wait_records = wait_registry.wait_records


@dataclass(frozen=True)
class RegisterGitHubPrWait:
    """Inputs registering one GitHub pull request wait."""

    root: Path
    pr_number: str
    repo: str | None = None
    platform: str = "codex"
    branch: str = ""
    head_sha: str = ""
    interval_seconds: int = 20
    timeout_seconds: int = 3600
    now: datetime | None = None


class WaitRegistry(BaseWaitRegistry):
    """File-backed durable Agent Maintainer wait records."""

    def register_github_pr(self, inputs: RegisterGitHubPrWait) -> WaitRecord:
        """Create and persist one pending GitHub pull request wait."""

        return self.register(
            RegisterWait(
                root=inputs.root,
                kind=WAIT_KIND_GITHUB_PR,
                target_id=inputs.pr_number,
                repo=inputs.repo,
                platform=inputs.platform,
                branch=inputs.branch,
                head_sha=inputs.head_sha,
                interval_seconds=inputs.interval_seconds,
                timeout_seconds=inputs.timeout_seconds,
                now=inputs.now,
            ),
        )

    def complete_github_pr(
        self,
        record: WaitRecord,
        result: GitHubPrWaitResult,
        *,
        now: datetime | None = None,
    ) -> WaitRecord:
        """Persist terminal GitHub pull request wait state."""

        return self.complete(
            record,
            terminal_result=_github_pr_terminal_result(result),
            state_data=_github_pr_state_data(result.state),
            resume_message=render_github_pr_wait_text(result),
            now=now,
        )


def observe_github_pr(
    registry: BaseWaitRegistry,
    record: WaitRecord,
    state: GitHubPrChecksState | None,
    *,
    now: datetime | None = None,
) -> WaitRecord:
    """Persist last observed non-terminal GitHub PR wait state."""

    return registry.observe(record, _github_pr_state_data(state), now=now)


def _github_pr_terminal_result(result: GitHubPrWaitResult) -> str:
    if result.error:
        return RESULT_ERROR
    if result.timed_out:
        return RESULT_TIMEOUT
    if result.state is None:
        return RESULT_UNKNOWN
    if result.state.succeeded:
        return RESULT_PASS
    return RESULT_FAIL


def _github_pr_state_data(state: GitHubPrChecksState | None) -> dict[str, object] | None:
    if state is None:
        return None
    return {
        "pr_number": state.pr_number,
        "completed": state.completed,
        "succeeded": state.succeeded,
        "checks": [_check_data(check) for check in state.checks],
    }


def _check_data(check: GitHubPrCheck) -> dict[str, object]:
    return {
        "name": check.name,
        "state": check.state,
        "conclusion": check.conclusion,
        "bucket": check.bucket,
        "link": check.link,
    }
