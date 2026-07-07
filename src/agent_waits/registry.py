"""Durable generic wait records for resumable agent handoffs."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final

from agent_waits.models import WaitRepairCapsule, render_wait_capsule

SCHEMA_VERSION: Final = 1
WAITS_DIR: Final = ".verify-logs/waits"
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
class RegisterWait:
    """Inputs registering one resumable wait."""

    root: Path
    kind: str
    target_id: str
    repo: str | None = None
    platform: str = "codex"
    branch: str = ""
    head_sha: str = ""
    interval_seconds: int = 20
    timeout_seconds: int = 3600
    resume_instruction: str = ""
    metadata: dict[str, object] | None = None
    now: datetime | None = None


@dataclass(frozen=True)
class WaitRecord:
    """Durable state for one resumable wait."""

    wait_id: str
    kind: str
    status: str
    target_id: str
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
    metadata: dict[str, object] | None = None
    schema_version: int = SCHEMA_VERSION

    @property
    def path_name(self) -> str:
        """Return safe JSON filename for this wait."""

        return f"{self.wait_id}.json"

    @property
    def ready(self) -> bool:
        """Return whether the wait has terminal continuation content."""

        return self.status == WAIT_STATUS_READY

    @property
    def pr_number(self) -> str:
        """Return compatibility PR number for PR wait records."""

        return self.target_id

    def as_dict(self) -> dict[str, object]:
        """Return stable JSON-safe wait record data."""

        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "wait_id": self.wait_id,
            "kind": self.kind,
            "status": self.status,
            "target_id": self.target_id,
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
            "metadata": self.metadata,
        }
        if self.kind == "github-pr":
            payload["pr_number"] = self.target_id
        return payload


class WaitRegistryError(ValueError):
    """Wait registry data is invalid or unavailable."""


class WaitRegistry:
    """File-backed durable wait records."""

    def __init__(self, root: Path) -> None:
        self.root = root

    @property
    def waits_dir(self) -> Path:
        """Return directory storing wait records."""

        return self.root / WAITS_DIR

    def register(self, inputs: RegisterWait) -> WaitRecord:
        """Create and persist one pending wait."""

        created_at = _timestamp(inputs.now)
        wait_id = _wait_id(inputs.kind, inputs.target_id, created_at)
        record = WaitRecord(
            wait_id=wait_id,
            kind=inputs.kind,
            status=WAIT_STATUS_PENDING,
            target_id=inputs.target_id,
            repo=inputs.repo,
            platform=inputs.platform,
            branch=inputs.branch,
            head_sha=inputs.head_sha,
            interval_seconds=inputs.interval_seconds,
            timeout_seconds=inputs.timeout_seconds,
            created_at=created_at,
            updated_at=created_at,
            deadline_at=_deadline(created_at, inputs.timeout_seconds),
            resume_instruction=inputs.resume_instruction
            or f"python -m agent_maintainer wait resume {wait_id}",
            metadata=_optional_mapping(inputs.metadata),
        )
        _write_record(self.waits_dir, record)
        return record

    def observe(
        self,
        record: WaitRecord,
        state_data: dict[str, object] | None,
        *,
        now: datetime | None = None,
    ) -> WaitRecord:
        """Persist the last observed non-terminal wait state."""

        observed = replace(
            record,
            updated_at=_timestamp(now),
            last_observed_state=state_data,
        )
        _write_record(self.waits_dir, observed)
        return observed

    def complete(
        self,
        record: WaitRecord,
        *,
        terminal_result: str,
        resume_message: str,
        state_data: dict[str, object] | None,
        now: datetime | None = None,
    ) -> WaitRecord:
        """Persist terminal wait state."""

        completed = replace(
            record,
            status=WAIT_STATUS_READY,
            updated_at=_timestamp(now),
            terminal_result=terminal_result,
            last_observed_state=state_data,
            resume_message=resume_message,
        )
        _write_record(self.waits_dir, completed)
        return completed

    def mark_resumed(
        self,
        record: WaitRecord,
        *,
        now: datetime | None = None,
    ) -> WaitRecord:
        """Mark wait record consumed by a continuation."""

        resumed = replace(record, status=WAIT_STATUS_RESUMED, updated_at=_timestamp(now))
        _write_record(self.waits_dir, resumed)
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


def wait_record_from_dict(payload: dict[str, object]) -> WaitRecord:
    """Build a wait record from JSON object data."""

    try:
        return WaitRecord(
            schema_version=_required_int(payload, "schema_version"),
            wait_id=str(payload["wait_id"]),
            kind=str(payload["kind"]),
            status=str(payload["status"]),
            target_id=_target_id(payload),
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
            metadata=_optional_mapping(payload.get("metadata")),
        )
    except KeyError as exc:
        raise WaitRegistryError(f"missing wait record field: {exc.args[0]}") from exc


def wait_records(registry: WaitRegistry) -> tuple[WaitRecord, ...]:
    """Return all wait records sorted by update time and id."""

    if not registry.waits_dir.exists():
        return ()
    records: list[WaitRecord] = []
    for path in registry.waits_dir.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            records.append(wait_record_from_dict(payload))
    return tuple(sorted(records, key=lambda record: (record.updated_at, record.wait_id)))


def render_resume_text(record: WaitRecord) -> str:
    """Render terminal wait continuation text."""

    if not record.ready:
        return render_wait_record_text(record)
    message = record.resume_message or render_wait_record_text(record)
    return "\n".join((message, "", "Continuation:", _continuation_prompt(record)))


def render_wait_record_text(record: WaitRecord) -> str:
    """Render compact wait record state."""

    result = record.terminal_result or RESULT_PENDING
    details = (
        f"kind: {record.kind}",
        f"target: {record.target_id}",
        f"status: {record.status}",
    )
    return render_wait_capsule(
        WaitRepairCapsule(
            result=result,
            run_id=record.wait_id,
            details=details,
            likely_next_action=record.resume_instruction if record.ready else "",
        ),
    )


def wait_record_json(record: WaitRecord) -> str:
    """Render wait record as stable JSON."""

    return json.dumps(record.as_dict(), indent=2, sort_keys=True)


def _continuation_prompt(record: WaitRecord) -> str:
    if record.kind == "github-pr":
        return (
            f"PR checks reached {record.terminal_result} for PR #{record.target_id}. "
            "Review the PR diff, inspect failures if any, merge only if satisfactory, "
            "then continue the prior roadmap task."
        )
    if record.kind == "github-run":
        return (
            f"GitHub run {record.target_id} reached {record.terminal_result}. "
            "Inspect failed jobs if any, repair or rerun only as needed, "
            "then continue the prior task."
        )
    if record.kind == "verifier":
        return (
            f"Verifier run {record.target_id} reached {record.terminal_result}. "
            "Inspect failed checks if any, repair the branch, then continue the prior task."
        )
    return (
        f"Wait {record.wait_id} reached {record.terminal_result}. "
        "Inspect failures if any, take appropriate follow-up, then continue the prior task."
    )


def _wait_id(kind: str, target_id: str, created_at: str) -> str:
    safe_timestamp = created_at.replace("-", "").replace(":", "").replace(".", "")
    safe_kind = _safe_segment(kind)
    safe_target = _safe_segment(target_id)
    return f"{safe_kind}-{safe_target}-{safe_timestamp}"


def _safe_segment(value: str) -> str:
    safe = "".join(character if character.isalnum() else "-" for character in value)
    return "-".join(part for part in safe.strip("-").split("-") if part) or "wait"


def _timestamp(now: datetime | None = None) -> str:
    current = now or datetime.now(UTC)
    return current.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _deadline(created_at: str, timeout_seconds: int) -> str:
    created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    deadline = created + timedelta(seconds=timeout_seconds)
    return deadline.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _write_record(waits_dir: Path, record: WaitRecord) -> None:
    waits_dir.mkdir(parents=True, exist_ok=True)
    path = waits_dir / record.path_name
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(wait_record_json(record), encoding="utf-8")
    tmp_path.replace(path)


def _target_id(payload: dict[str, object]) -> str:
    target = payload.get("target_id", payload.get("pr_number"))
    if target is None:
        raise WaitRegistryError("missing wait record field: target_id")
    return str(target)


def _required_int(payload: dict[str, object], field: str) -> int:
    value = payload[field]
    if not isinstance(value, int):
        raise WaitRegistryError(f"wait record field must be int: {field}")
    return value


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_mapping(value: object) -> dict[str, object] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise WaitRegistryError("wait record mapping field must be an object")
    return dict(value)
