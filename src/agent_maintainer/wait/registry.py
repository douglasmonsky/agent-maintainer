"""Agent Maintainer wait registry adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final

from agent_maintainer.wait.github import (
    GitHubJob,
    GitHubRunState,
    GitHubWaitResult,
    render_github_wait_text,
)
from agent_maintainer.wait.github_pr import (
    GitHubPrCheck,
    GitHubPrChecksState,
    GitHubPrWaitResult,
    render_github_pr_wait_text,
)
from agent_maintainer.wait.verifier import VerifierWaitResult, render_verifier_wait_text
from agent_maintainer.wait.verifier_manifest import VerifierManifest
from agent_waits import constants as wait_constants
from agent_waits import registry as wait_registry
from agent_waits import rendering as wait_rendering

WAIT_KIND_GITHUB_PR: Final = "github-pr"
WAIT_KIND_GITHUB_RUN: Final = "github-run"
WAIT_KIND_VERIFIER: Final = "verifier"
VERIFIER_LOG_DIR_METADATA: Final = "log_dir"

RESULT_ERROR = wait_constants.RESULT_ERROR
RESULT_FAIL = wait_constants.RESULT_FAIL
RESULT_PASS = wait_constants.RESULT_PASS
RESULT_PENDING = wait_constants.RESULT_PENDING
RESULT_TIMEOUT = wait_constants.RESULT_TIMEOUT
RESULT_CANCELLED: Final = "CANCELLED"
RESULT_UNKNOWN: Final = "UNKNOWN"
SCHEMA_VERSION: Final = 1
WAIT_STATUS_PENDING = wait_constants.WAIT_STATUS_PENDING
WAIT_STATUS_READY = wait_constants.WAIT_STATUS_READY
WAIT_STATUS_NOTIFYING = wait_constants.WAIT_STATUS_NOTIFYING
WAIT_STATUS_NOTIFY_FAILED = wait_constants.WAIT_STATUS_NOTIFY_FAILED
WAIT_STATUS_RESUMED = wait_constants.WAIT_STATUS_RESUMED
WAIT_STATUS_EXPIRED_READY = wait_constants.WAIT_STATUS_EXPIRED_READY
WAITS_DIR = wait_constants.WAITS_DIR
WaitRegistryError = wait_registry.WaitRegistryError
expire_ready_records = wait_registry.expire_ready_records
RegisterWait = wait_registry.RegisterWait
WaitRecord = wait_registry.WaitRecord
BaseWaitRegistry = wait_registry.WaitRegistry
render_resume_text = wait_rendering.render_resume_text
render_wait_record_text = wait_rendering.render_wait_record_text
wait_record_from_dict = wait_registry.wait_record_from_dict
wait_record_json = wait_rendering.wait_record_json
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


@dataclass(frozen=True)
class RegisterGitHubRunWait:
    """Inputs registering one GitHub Actions run wait."""

    root: Path
    run_id: str
    repo: str | None = None
    platform: str = "codex"
    branch: str = ""
    head_sha: str = ""
    interval_seconds: int = 20
    timeout_seconds: int = 3600
    now: datetime | None = None


@dataclass(frozen=True)
class RegisterVerifierWait:
    """Inputs registering one verifier run wait."""

    root: Path
    run_id: str
    platform: str = "codex"
    log_dir: Path = Path(".verify-logs")
    branch: str = ""
    head_sha: str = ""
    interval_seconds: int = 5
    timeout_seconds: int = 3600
    now: datetime | None = None


class WaitRegistry(BaseWaitRegistry):
    """Agent Maintainer wait registry convenience methods."""

    def register_github_pr(self, wait: RegisterGitHubPrWait) -> WaitRecord:
        """Register one GitHub PR wait."""

        return self.register(
            RegisterWait(
                root=wait.root,
                kind=WAIT_KIND_GITHUB_PR,
                target_id=wait.pr_number,
                repo=wait.repo,
                platform=wait.platform,
                branch=wait.branch,
                head_sha=wait.head_sha,
                interval_seconds=wait.interval_seconds,
                timeout_seconds=wait.timeout_seconds,
                now=wait.now,
            ),
        )

    def register_github_run(self, wait: RegisterGitHubRunWait) -> WaitRecord:
        """Register one GitHub Actions run wait."""

        return self.register(
            RegisterWait(
                root=wait.root,
                kind=WAIT_KIND_GITHUB_RUN,
                target_id=wait.run_id,
                repo=wait.repo,
                platform=wait.platform,
                branch=wait.branch,
                head_sha=wait.head_sha,
                interval_seconds=wait.interval_seconds,
                timeout_seconds=wait.timeout_seconds,
                now=wait.now,
            ),
        )

    def register_verifier(self, wait: RegisterVerifierWait) -> WaitRecord:
        """Register one verifier run wait."""

        return self.register(
            RegisterWait(
                root=wait.root,
                kind=WAIT_KIND_VERIFIER,
                target_id=wait.run_id,
                platform=wait.platform,
                branch=wait.branch,
                head_sha=wait.head_sha,
                interval_seconds=wait.interval_seconds,
                timeout_seconds=wait.timeout_seconds,
                metadata={VERIFIER_LOG_DIR_METADATA: str(wait.log_dir)},
                now=wait.now,
            ),
        )

    def complete_github_pr(
        self,
        record: WaitRecord,
        result: GitHubPrWaitResult,
        *,
        now: datetime | None = None,
    ) -> WaitRecord:
        """Persist terminal GitHub PR result."""

        return self.complete(
            record,
            terminal_result=_github_pr_terminal_result(result),
            resume_message=render_github_pr_wait_text(result),
            state_data=_github_pr_state_data(result.state),
            now=now,
        )

    def complete_github_run(
        self,
        record: WaitRecord,
        result: GitHubWaitResult,
        *,
        now: datetime | None = None,
    ) -> WaitRecord:
        """Persist terminal GitHub run result."""

        return self.complete(
            record,
            terminal_result=_github_run_terminal_result(result),
            resume_message=render_github_wait_text(result),
            state_data=_github_run_state_data(result.state),
            now=now,
        )

    def complete_verifier(
        self,
        record: WaitRecord,
        result: VerifierWaitResult,
        *,
        now: datetime | None = None,
    ) -> WaitRecord:
        """Persist terminal verifier result."""

        return self.complete(
            record,
            terminal_result=_verifier_terminal_result(result),
            resume_message=render_verifier_wait_text(result),
            state_data=_verifier_state_data(result),
            now=now,
        )


def observe_github_pr(
    registry: WaitRegistry,
    record: WaitRecord,
    state: GitHubPrChecksState | None,
    *,
    now: datetime | None = None,
) -> WaitRecord:
    """Persist last observed non-terminal GitHub PR wait state."""

    return registry.observe(record, _github_pr_state_data(state), now=now)


def observe_github_run(
    registry: WaitRegistry,
    record: WaitRecord,
    state: GitHubRunState | None,
    *,
    now: datetime | None = None,
) -> WaitRecord:
    """Persist last observed non-terminal GitHub run state."""

    return registry.observe(record, _github_run_state_data(state), now=now)


def observe_verifier(
    registry: WaitRegistry,
    record: WaitRecord,
    manifest: VerifierManifest | None,
    *,
    now: datetime | None = None,
) -> WaitRecord:
    """Persist last observed non-terminal verifier state."""

    result = VerifierWaitResult(run_id=record.target_id, manifest=manifest)
    return registry.observe(record, _verifier_state_data(result), now=now)


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


def _github_run_terminal_result(result: GitHubWaitResult) -> str:
    if result.error:
        return RESULT_ERROR
    if result.timed_out:
        return RESULT_TIMEOUT
    if result.state is None:
        return RESULT_UNKNOWN
    if result.state.succeeded:
        return RESULT_PASS
    return RESULT_FAIL


def _verifier_terminal_result(result: VerifierWaitResult) -> str:
    if result.cancelled:
        terminal_result = RESULT_CANCELLED
    elif result.error:
        terminal_result = RESULT_ERROR
    elif result.timed_out:
        terminal_result = RESULT_TIMEOUT
    else:
        terminal_result = _verifier_manifest_result(result.manifest)
    return terminal_result


def _verifier_manifest_result(manifest: VerifierManifest | None) -> str:
    if manifest is None:
        return RESULT_UNKNOWN
    if manifest.succeeded:
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


def _github_run_state_data(state: GitHubRunState | None) -> dict[str, object] | None:
    if state is None:
        return None
    return {
        "status": state.status,
        "conclusion": state.conclusion,
        "url": state.url,
        "completed": state.completed,
        "succeeded": state.succeeded,
        "jobs": [_job_data(job) for job in state.jobs],
    }


def _verifier_state_data(result: VerifierWaitResult) -> dict[str, object] | None:
    manifest = result.manifest
    if manifest is None:
        return {
            "manifest_found": False,
            "cancelled": result.cancelled,
            "error": result.error,
            "process_exit_code": result.process_exit_code,
        }
    return {
        "manifest_found": True,
        "run_id": manifest.run_id,
        "profile": manifest.profile,
        "succeeded": manifest.succeeded,
        "failed_checks": [check.name for check in manifest.failed_checks],
    }


def _check_data(check: GitHubPrCheck) -> dict[str, object]:
    return {
        "name": check.name,
        "state": check.state,
        "conclusion": check.conclusion,
        "bucket": check.bucket,
        "link": check.link,
    }


def _job_data(job: GitHubJob) -> dict[str, object]:
    return {
        "name": job.name,
        "status": job.status,
        "conclusion": job.conclusion,
        "url": job.url,
    }
