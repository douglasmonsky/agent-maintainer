"""Known wait-kind handlers for background sweeps."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from agent_maintainer.wait import registry as wait_registry
from agent_maintainer.wait.github import (
    GitHubWaitConfig,
    GitHubWaitResult,
    QueryRun,
    query_github_run,
)
from agent_maintainer.wait.github_pr import (
    GitHubPrWaitConfig,
    GitHubPrWaitResult,
    QueryPrChecks,
    query_github_pr_checks,
)
from agent_maintainer.wait.verifier import (
    VerifierWaitConfig,
    VerifierWaitResult,
    query_verifier_run_once,
)

VerifierQuery = Callable[[VerifierWaitConfig], VerifierWaitResult | None]


@dataclass(frozen=True)
class WaitRegistration:
    """Common wait registration data passed to known handlers."""

    root: Path
    target_id: str
    repo: str | None = None
    platform: str = "codex"
    branch: str = ""
    head_sha: str = ""
    interval_seconds: int = 20
    timeout_seconds: int = 3600
    log_dir: Path = Path(".verify-logs")


@dataclass(frozen=True)
class WaitQueries:
    """Optional test query overrides for one sweep."""

    query_pr_checks: QueryPrChecks | None = None
    query_github_run: QueryRun | None = None
    query_verifier: VerifierQuery | None = None


class WaitHandler(Protocol):
    """Known wait-kind behavior used by register, sweep, and resume."""

    kind: str

    def register(
        self,
        registry: wait_registry.WaitRegistry,
        registration: WaitRegistration,
    ) -> wait_registry.WaitRecord:
        """Register one wait of this kind."""
        raise NotImplementedError

    def poll_once(
        self,
        registry: wait_registry.WaitRegistry,
        record: wait_registry.WaitRecord,
        *,
        queries: WaitQueries,
        now: datetime | None = None,
    ) -> wait_registry.WaitRecord:
        """Poll this wait once and persist any meaningful state change."""
        raise NotImplementedError

    def render_resume(self, record: wait_registry.WaitRecord) -> str:
        """Render terminal resume text for this wait."""
        raise NotImplementedError

    def continuation_prompt(self, record: wait_registry.WaitRecord) -> str:
        """Return Codex continuation prompt for this wait."""
        raise NotImplementedError


class GitHubPrWaitHandler:
    """Background handler for GitHub pull request check waits."""

    kind = wait_registry.WAIT_KIND_GITHUB_PR

    def register(
        self,
        registry: wait_registry.WaitRegistry,
        registration: WaitRegistration,
    ) -> wait_registry.WaitRecord:
        """Register one GitHub PR wait."""

        return registry.register_github_pr(
            wait_registry.RegisterGitHubPrWait(
                root=registration.root,
                pr_number=registration.target_id,
                repo=registration.repo,
                platform=registration.platform,
                branch=registration.branch,
                head_sha=registration.head_sha,
                interval_seconds=registration.interval_seconds,
                timeout_seconds=registration.timeout_seconds,
            ),
        )

    def poll_once(
        self,
        registry: wait_registry.WaitRegistry,
        record: wait_registry.WaitRecord,
        *,
        queries: WaitQueries,
        now: datetime | None = None,
    ) -> wait_registry.WaitRecord:
        """Poll GitHub PR checks once."""

        query = queries.query_pr_checks or query_github_pr_checks
        try:
            state = query(_github_pr_config(record))
        except RuntimeError as exc:
            return registry.complete_github_pr(
                record,
                GitHubPrWaitResult(
                    pr_number=record.target_id,
                    state=None,
                    error=str(exc),
                ),
                now=now,
            )
        if state.completed:
            return registry.complete_github_pr(
                record,
                GitHubPrWaitResult(pr_number=record.target_id, state=state),
                now=now,
            )
        observed = wait_registry.observe_github_pr(registry, record, state, now=now)
        if _timed_out(observed, now):
            return registry.complete_github_pr(
                observed,
                GitHubPrWaitResult(
                    pr_number=observed.target_id,
                    state=state,
                    timed_out=True,
                ),
                now=now,
            )
        return observed

    def render_resume(self, record: wait_registry.WaitRecord) -> str:
        """Render terminal resume text."""

        return wait_registry.render_resume_text(record)

    def continuation_prompt(self, record: wait_registry.WaitRecord) -> str:
        """Return Codex continuation prompt for a terminal PR wait."""

        return (
            f"PR checks reached {record.terminal_result} for PR #{record.target_id}. "
            "Review the PR diff, inspect failures if any, merge only if satisfactory, "
            "then continue the prior roadmap task."
        )


class GitHubRunWaitHandler:
    """Background handler for GitHub Actions run waits."""

    kind = wait_registry.WAIT_KIND_GITHUB_RUN

    def register(
        self,
        registry: wait_registry.WaitRegistry,
        registration: WaitRegistration,
    ) -> wait_registry.WaitRecord:
        """Register one GitHub Actions run wait."""

        return registry.register_github_run(
            wait_registry.RegisterGitHubRunWait(
                root=registration.root,
                run_id=registration.target_id,
                repo=registration.repo,
                platform=registration.platform,
                branch=registration.branch,
                head_sha=registration.head_sha,
                interval_seconds=registration.interval_seconds,
                timeout_seconds=registration.timeout_seconds,
            ),
        )

    def poll_once(
        self,
        registry: wait_registry.WaitRegistry,
        record: wait_registry.WaitRecord,
        *,
        queries: WaitQueries,
        now: datetime | None = None,
    ) -> wait_registry.WaitRecord:
        """Poll one GitHub Actions run once."""

        query = queries.query_github_run or query_github_run
        try:
            state = query(_github_run_config(record))
        except RuntimeError as exc:
            return registry.complete_github_run(
                record,
                GitHubWaitResult(
                    run_id=record.target_id,
                    state=None,
                    error=str(exc),
                ),
                now=now,
            )
        if state.completed:
            return registry.complete_github_run(
                record,
                GitHubWaitResult(run_id=record.target_id, state=state),
                now=now,
            )
        observed = wait_registry.observe_github_run(registry, record, state, now=now)
        if _timed_out(observed, now):
            return registry.complete_github_run(
                observed,
                GitHubWaitResult(
                    run_id=observed.target_id,
                    state=state,
                    timed_out=True,
                ),
                now=now,
            )
        return observed

    def render_resume(self, record: wait_registry.WaitRecord) -> str:
        """Render terminal resume text."""

        return wait_registry.render_resume_text(record)

    def continuation_prompt(self, record: wait_registry.WaitRecord) -> str:
        """Return Codex continuation prompt for a terminal GitHub run wait."""

        return (
            f"GitHub Actions run {record.target_id} reached {record.terminal_result}. "
            "Review failed jobs if any, repair or rerun only as needed, "
            "then continue the prior task."
        )


class VerifierWaitHandler:
    """Background handler for local verifier waits."""

    kind = wait_registry.WAIT_KIND_VERIFIER

    def register(
        self,
        registry: wait_registry.WaitRegistry,
        registration: WaitRegistration,
    ) -> wait_registry.WaitRecord:
        """Register one verifier run wait."""

        return registry.register_verifier(
            wait_registry.RegisterVerifierWait(
                root=registration.root,
                run_id=registration.target_id,
                platform=registration.platform,
                log_dir=registration.log_dir,
                branch=registration.branch,
                head_sha=registration.head_sha,
                interval_seconds=registration.interval_seconds,
                timeout_seconds=registration.timeout_seconds,
            ),
        )

    def poll_once(
        self,
        registry: wait_registry.WaitRegistry,
        record: wait_registry.WaitRecord,
        *,
        queries: WaitQueries,
        now: datetime | None = None,
    ) -> wait_registry.WaitRecord:
        """Poll one local verifier manifest once."""

        query = queries.query_verifier or query_verifier_once
        result = query(_verifier_config(record))
        if result is not None:
            return registry.complete_verifier(record, result, now=now)
        observed = wait_registry.observe_verifier(registry, record, None, now=now)
        if _timed_out(observed, now):
            return registry.complete_verifier(
                observed,
                VerifierWaitResult(
                    run_id=observed.target_id,
                    manifest=None,
                    timed_out=True,
                ),
                now=now,
            )
        return observed

    def render_resume(self, record: wait_registry.WaitRecord) -> str:
        """Render terminal resume text."""

        return wait_registry.render_resume_text(record)

    def continuation_prompt(self, record: wait_registry.WaitRecord) -> str:
        """Return Codex continuation prompt for a terminal verifier wait."""

        return (
            f"Verifier run {record.target_id} reached {record.terminal_result}. "
            "Review failed checks if any, repair the branch, then continue the prior task."
        )


HANDLERS: tuple[tuple[str, WaitHandler], ...] = (
    (wait_registry.WAIT_KIND_GITHUB_PR, GitHubPrWaitHandler()),
    (wait_registry.WAIT_KIND_GITHUB_RUN, GitHubRunWaitHandler()),
    (wait_registry.WAIT_KIND_VERIFIER, VerifierWaitHandler()),
)


def handler_for(kind: str) -> WaitHandler:
    """Return wait handler for a known wait kind."""

    for handler_kind, handler in HANDLERS:
        if handler_kind == kind:
            return handler
    raise wait_registry.WaitRegistryError(f"unknown wait kind: {kind}")


def continuation_prompt(record: wait_registry.WaitRecord) -> str:
    """Return handler-specific Codex continuation prompt."""

    return handler_for(record.kind).continuation_prompt(record)


def query_verifier_once(config: VerifierWaitConfig) -> VerifierWaitResult | None:
    """Return terminal verifier result, otherwise pending."""

    return query_verifier_run_once(config)


def _github_pr_config(record: wait_registry.WaitRecord) -> GitHubPrWaitConfig:
    return GitHubPrWaitConfig(
        pr_number=record.target_id,
        repo=record.repo,
        interval_seconds=record.interval_seconds,
        timeout_seconds=record.timeout_seconds,
    )


def _github_run_config(record: wait_registry.WaitRecord) -> GitHubWaitConfig:
    return GitHubWaitConfig(
        run_id=record.target_id,
        repo=record.repo,
        interval_seconds=record.interval_seconds,
        timeout_seconds=record.timeout_seconds,
    )


def _verifier_config(record: wait_registry.WaitRecord) -> VerifierWaitConfig:
    return VerifierWaitConfig(
        run_id=record.target_id,
        log_dir=_verifier_log_dir(record),
        interval_seconds=record.interval_seconds,
        timeout_seconds=record.timeout_seconds,
    )


def _verifier_log_dir(record: wait_registry.WaitRecord) -> Path:
    metadata = record.metadata or {}
    value = metadata.get(wait_registry.VERIFIER_LOG_DIR_METADATA, ".verify-logs")
    return Path(str(value))


def _timed_out(record: wait_registry.WaitRecord, now: datetime | None) -> bool:
    deadline = datetime.fromisoformat(record.deadline_at.replace("Z", "+00:00"))
    current = now or datetime.now(UTC)
    return current.astimezone(UTC) >= deadline
