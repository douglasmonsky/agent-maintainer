"""Durable wait registry for resumable wait handoffs."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final

from agent_maintainer.wait.github_pr import (
    GitHubPrCheck,
    GitHubPrChecksState,
    GitHubPrWaitResult,
    render_github_pr_wait_text,
)
from agent_maintainer.wait.models import WaitRepairCapsule, render_wait_capsule

SCHEMA_VERSION: Final = 1
WAITS_DIR: Final = ".verify-logs/waits"
WAIT_KIND_GITHUB_PR: Final = "github-pr"
WAIT_STATUS_PENDING: Final = "pending"
WAIT_STATUS_READY: Final = "ready_for_manual_resume"
WAIT_STATUS_RESUMED: Final = "resumed"
RESULT_PENDING: Final = "PENDING"
RESULT_PASS: Final = "PASS"
RESULT_FAIL: Final = "FAIL"
RESULT_TIMEOUT: Final = "TIMEOUT"
RESULT_ERROR: Final = "ERROR"
RESULT_UNKNOWN: Final = "UNKNOWN"


@dataclass(frozen=True)
class RegisterGitHubPrWait:
    """Inputs for registering one GitHub pull request wait."""

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
class WaitRecord:
    """Durable state for one resumable wait."""

    wait_id: str
    kind: str
    status: str
    pr_number: str
    repo: str | None
    platform: str
    branch: str
    head_sha: str
    interval_seconds: int
    timeout_seconds: int
    created_at: str
    updated_at: str
    deadline_at: str
    resume_instruction: str
    terminal_result: str = ""
    last_observed_state: dict[str, object] | None = None
    resume_message: str = ""
    schema_version: int = SCHEMA_VERSION

    @property
    def path_name(self) -> str:
        """Return registry filename for this wait."""

        return f"{self.wait_id}.json"

    @property
    def ready(self) -> bool:
        """Return whether a terminal result is ready for continuation."""

        return self.status == WAIT_STATUS_READY and bool(self.terminal_result)

    def as_dict(self) -> dict[str, object]:
        """Return JSON-safe wait record data."""

        return {
            "schema_version": self.schema_version,
            "wait_id": self.wait_id,
            "kind": self.kind,
            "status": self.status,
            "pr_number": self.pr_number,
            "repo": self.repo,
            "platform": self.platform,
            "branch": self.branch,
            "head_sha": self.head_sha,
            "interval_seconds": self.interval_seconds,
            "timeout_seconds": self.timeout_seconds,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "deadline_at": self.deadline_at,
            "last_observed_state": self.last_observed_state,
            "terminal_result": self.terminal_result,
            "resume_instruction": self.resume_instruction,
            "resume_message": self.resume_message,
        }


class WaitRegistryError(ValueError):
    """Wait registry data is invalid or unavailable."""


class WaitRegistry:
    """File-backed registry for durable wait records."""

    def __init__(self, root: Path) -> None:
        self.root = root

    @property
    def waits_dir(self) -> Path:
        """Return directory storing wait records."""

        return self.root / WAITS_DIR

    def register_github_pr(self, inputs: RegisterGitHubPrWait) -> WaitRecord:
        """Create and persist one pending GitHub pull request wait."""

        created_at = _timestamp(inputs.now)
        wait_id = _github_pr_wait_id(inputs.pr_number, created_at)
        record = WaitRecord(
            wait_id=wait_id,
            kind=WAIT_KIND_GITHUB_PR,
            status=WAIT_STATUS_PENDING,
            pr_number=inputs.pr_number,
            repo=inputs.repo,
            platform=inputs.platform,
            branch=inputs.branch,
            head_sha=inputs.head_sha,
            interval_seconds=inputs.interval_seconds,
            timeout_seconds=inputs.timeout_seconds,
            created_at=created_at,
            updated_at=created_at,
            deadline_at=_deadline(created_at, inputs.timeout_seconds),
            resume_instruction=f"python -m agent_maintainer wait resume {wait_id}",
        )
        self.write(record)
        return record

    def complete_github_pr(
        self,
        record: WaitRecord,
        result: GitHubPrWaitResult,
        *,
        now: datetime | None = None,
    ) -> WaitRecord:
        """Persist terminal GitHub pull request wait state."""

        completed = replace(
            record,
            status=WAIT_STATUS_READY,
            updated_at=_timestamp(now),
            terminal_result=_github_pr_terminal_result(result),
            last_observed_state=_github_pr_state_data(result.state),
            resume_message=render_github_pr_wait_text(result),
        )
        self.write(completed)
        return completed

    def mark_resumed(
        self,
        record: WaitRecord,
        *,
        now: datetime | None = None,
    ) -> WaitRecord:
        """Mark a wait record as consumed by a continuation."""

        resumed = replace(record, status=WAIT_STATUS_RESUMED, updated_at=_timestamp(now))
        self.write(resumed)
        return resumed

    def read(self, wait_id: str) -> WaitRecord:
        """Read one wait record by id."""

        path = self.waits_dir / f"{wait_id}.json"
        if not path.exists():
            raise WaitRegistryError(f"wait record not found: {wait_id}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise WaitRegistryError(f"wait record is not an object: {wait_id}")
        return wait_record_from_dict(payload)

    def write(self, record: WaitRecord) -> None:
        """Atomically persist one wait record."""

        self.waits_dir.mkdir(parents=True, exist_ok=True)
        path = self.waits_dir / record.path_name
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(record.as_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)


def wait_record_from_dict(payload: dict[str, object]) -> WaitRecord:
    """Build a wait record from JSON object data."""

    try:
        return WaitRecord(
            schema_version=_required_int(payload, "schema_version"),
            wait_id=str(payload["wait_id"]),
            kind=str(payload["kind"]),
            status=str(payload["status"]),
            pr_number=str(payload["pr_number"]),
            repo=_optional_text(payload.get("repo")),
            platform=str(payload["platform"]),
            branch=str(payload.get("branch", "")),
            head_sha=str(payload.get("head_sha", "")),
            interval_seconds=_required_int(payload, "interval_seconds"),
            timeout_seconds=_required_int(payload, "timeout_seconds"),
            created_at=str(payload["created_at"]),
            updated_at=str(payload["updated_at"]),
            deadline_at=str(payload["deadline_at"]),
            last_observed_state=_optional_mapping(payload.get("last_observed_state")),
            terminal_result=str(payload.get("terminal_result", "")),
            resume_instruction=str(payload["resume_instruction"]),
            resume_message=str(payload.get("resume_message", "")),
        )
    except KeyError as exc:
        raise WaitRegistryError(f"missing wait record field: {exc.args[0]}") from exc


def render_wait_record_text(record: WaitRecord) -> str:
    """Render compact wait registration output."""

    return render_wait_capsule(
        WaitRepairCapsule(
            result=record.terminal_result or RESULT_PENDING,
            run_id=record.wait_id,
            details=(_wait_detail(record),),
            likely_next_action=record.resume_instruction,
        ),
    )


def render_resume_text(record: WaitRecord) -> str:
    """Render compact resume text for one wait record."""

    if not record.ready:
        return render_wait_record_text(record)
    continuation = (
        f"PR checks reached {record.terminal_result} for PR #{record.pr_number}. "
        "Review the PR diff, inspect failures if any, merge only if satisfactory, "
        "then continue the prior roadmap task."
    )
    return f"{record.resume_message}\n\nContinuation:\n{continuation}"


def wait_record_json(record: WaitRecord) -> str:
    """Render one wait record as stable JSON."""

    return json.dumps(record.as_dict(), indent=2, sort_keys=True)


def _github_pr_wait_id(pr_number: str, created_at: str) -> str:
    safe_timestamp = created_at.replace("-", "").replace(":", "").replace(".", "").replace("Z", "Z")
    return f"github-pr-{pr_number}-{safe_timestamp}"


def _timestamp(now: datetime | None = None) -> str:
    value = now or datetime.now(UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _deadline(created_at: str, timeout_seconds: int) -> str:
    created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    return _timestamp(created + timedelta(seconds=timeout_seconds))


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


def _github_pr_state_data(
    state: GitHubPrChecksState | None,
) -> dict[str, object] | None:
    if state is None:
        return None
    return {
        "pr_number": state.pr_number,
        "completed": state.completed,
        "succeeded": state.succeeded,
        "checks": [_check_data(check) for check in state.checks],
    }


def _check_data(check: GitHubPrCheck) -> dict[str, str]:
    return {
        "name": check.name,
        "state": check.state,
        "conclusion": check.conclusion,
        "bucket": check.bucket,
        "link": check.link,
    }


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _required_int(payload: dict[str, object], field: str) -> int:
    value = payload[field]
    if isinstance(value, (int, str)):
        return int(value)
    raise WaitRegistryError(f"{field} must be an integer")


def _optional_mapping(value: object) -> dict[str, object] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return dict(value)
    raise WaitRegistryError("last_observed_state must be an object")


def _wait_detail(record: WaitRecord) -> str:
    repo = f" repo={record.repo}" if record.repo else ""
    return f"{record.kind} pr={record.pr_number} platform={record.platform}{repo}"
