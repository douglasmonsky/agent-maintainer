"""Durable generic wait records for resumable agent handoffs."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

from agent_waits import constants as wait_constants
from agent_waits import heartbeat as wait_heartbeat
from agent_waits.record_lock import wait_record_lock


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
    schema_version: int = 1

    @property
    def path_name(self) -> str:
        """Return safe JSON filename for this wait."""

        return f"{self.wait_id}.json"

    @property
    def ready(self) -> bool:
        """Return whether the wait has terminal continuation content."""

        return self.status in {
            wait_constants.WAIT_STATUS_READY,
            wait_constants.WAIT_STATUS_NOTIFY_FAILED,
        }

    @property
    def notification_ready(self) -> bool:
        """Return whether automatic notification may be claimed once."""

        return self.status == wait_constants.WAIT_STATUS_READY

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
        self.waits_dir = root / wait_constants.WAITS_DIR

    def register(self, inputs: RegisterWait) -> WaitRecord:
        """Create and persist one pending wait."""

        existing = max(
            (
                record
                for record in wait_records(self)
                if _same_identity(
                    record,
                    kind=inputs.kind,
                    target_id=inputs.target_id,
                    repo=inputs.repo,
                    head_sha=inputs.head_sha,
                )
                and record.status
                in {
                    wait_constants.WAIT_STATUS_PENDING,
                    wait_constants.WAIT_STATUS_READY,
                    wait_constants.WAIT_STATUS_NOTIFYING,
                    wait_constants.WAIT_STATUS_NOTIFY_FAILED,
                }
            ),
            key=lambda record: record.created_at,
            default=None,
        )
        if existing is not None:
            return existing
        created_at = _timestamp(inputs.now)
        wait_id = _wait_id(inputs.kind, inputs.target_id, created_at)
        record = WaitRecord(
            wait_id=wait_id,
            kind=inputs.kind,
            status=wait_constants.WAIT_STATUS_PENDING,
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
            metadata=wait_heartbeat.registration_metadata(
                _optional_mapping(inputs.metadata),
            ),
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

        with wait_record_lock(self.waits_dir, record.wait_id):
            current = self.read(record.wait_id)
            if current.status != wait_constants.WAIT_STATUS_PENDING:
                return current
            observed = replace(
                current,
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

        with wait_record_lock(self.waits_dir, record.wait_id):
            current = self.read(record.wait_id)
            if current.status != wait_constants.WAIT_STATUS_PENDING:
                return current
            completed = replace(
                current,
                status=wait_constants.WAIT_STATUS_READY,
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

        with wait_record_lock(self.waits_dir, record.wait_id):
            current = self.read(record.wait_id)
            resumed = replace(
                current,
                status=wait_constants.WAIT_STATUS_RESUMED,
                updated_at=_timestamp(now),
            )
            _write_record(self.waits_dir, resumed)
            return resumed

    def read(self, wait_id: str) -> WaitRecord:
        """Read one wait record by id."""

        path = self.waits_dir / f"{wait_id}.json"
        if not path.exists():
            raise WaitRegistryError(f"wait record not found: {wait_id}")
        try:
            parsed = _optional_mapping(cast(object, json.loads(path.read_text(encoding="utf-8"))))
        except WaitRegistryError as exc:
            raise WaitRegistryError(f"wait record is not an object: {wait_id}") from exc
        if parsed is None:
            raise WaitRegistryError(f"wait record is not an object: {wait_id}")
        return wait_record_from_dict(parsed)

    def claim_ready_for_notification(
        self,
        *,
        now: datetime | None = None,
    ) -> tuple[WaitRecord, ...]:
        """Claim ready repo-heartbeat records that have not notified yet."""

        claimed: list[WaitRecord] = []
        timestamp = _timestamp(now)
        for record in wait_records(self):
            with wait_record_lock(self.waits_dir, record.wait_id):
                current = self.read(record.wait_id)
                if not _repo_heartbeat_ready(current):
                    continue
                metadata = dict(current.metadata or {})
                metadata[wait_heartbeat.HEARTBEAT_NOTIFIED_AT_METADATA] = timestamp
                notified = replace(current, updated_at=timestamp, metadata=metadata)
                _write_record(self.waits_dir, notified)
                claimed.append(notified)
        return tuple(claimed)


def expire_ready_records(
    registry: WaitRegistry,
    *,
    older_than_seconds: int,
    now: datetime | None = None,
) -> tuple[WaitRecord, ...]:
    """Mark stale ready records expired so heartbeats ignore them."""

    expired: list[WaitRecord] = []
    timestamp = _timestamp(now)
    current = _parse_timestamp(timestamp)
    for record in wait_records(registry):
        with wait_record_lock(registry.waits_dir, record.wait_id):
            latest = registry.read(record.wait_id)
            if not _stale_ready(latest, current, older_than_seconds):
                continue
            metadata = dict(latest.metadata or {})
            metadata["expired_reason"] = "ready_ttl"
            updated = replace(
                latest,
                status=wait_constants.WAIT_STATUS_EXPIRED_READY,
                updated_at=timestamp,
                metadata=metadata,
            )
            _write_record(registry.waits_dir, updated)
            expired.append(updated)
    return tuple(expired)


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
        payload: object = json.loads(path.read_text(encoding="utf-8"))
        try:
            parsed = _optional_mapping(payload)
        except WaitRegistryError:
            continue
        if parsed is not None:
            records.append(wait_record_from_dict(parsed))
    return tuple(sorted(records, key=lambda record: (record.updated_at, record.wait_id)))


def _repo_heartbeat_ready(record: WaitRecord) -> bool:
    return record.ready and wait_heartbeat.repo_heartbeat_ready(record.metadata)


def _same_identity(
    record: WaitRecord,
    *,
    kind: str,
    target_id: str,
    repo: str | None,
    head_sha: str,
) -> bool:
    if record.kind != kind or record.target_id != target_id:
        return False
    if kind == "github-pr":
        return record.repo == repo and record.head_sha == head_sha
    if kind == "github-run":
        return record.repo == repo
    if kind == "verifier":
        return record.head_sha == head_sha
    return record.repo == repo and record.head_sha == head_sha


def _stale_ready(
    record: WaitRecord,
    now: datetime,
    older_than_seconds: int,
) -> bool:
    if not record.ready or older_than_seconds < 0:
        return False
    updated_at = _parse_timestamp(record.updated_at)
    return (now - updated_at).total_seconds() >= older_than_seconds


def _wait_id(kind: str, target_id: str, created_at: str) -> str:
    safe_timestamp = created_at.replace("-", "").replace(":", "").replace(".", "")
    return f"{_safe_segment(kind)}-{_safe_segment(target_id)}-{safe_timestamp}"


def _safe_segment(value: str) -> str:
    safe = "".join(character if character.isalnum() else "-" for character in value)
    return "-".join(part for part in safe.strip("-").split("-") if part) or "wait"


def _timestamp(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _deadline(created_at: str, timeout_seconds: int) -> str:
    created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    deadline = created + timedelta(seconds=timeout_seconds)
    return deadline.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _write_record(waits_dir: Path, record: WaitRecord) -> None:
    waits_dir.mkdir(parents=True, exist_ok=True)
    path = waits_dir / record.path_name
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(record.as_dict(), indent=2, sort_keys=True), encoding="utf-8")
    tmp_path.replace(path)


format_timestamp, parse_timestamp, write_record = _timestamp, _parse_timestamp, _write_record


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
    return None if value is None else str(value)


def _optional_mapping(value: object) -> dict[str, object] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise WaitRegistryError("wait record mapping field must be an object")
    mapping = cast(dict[object, object], value)
    if not all(isinstance(key, str) for key in mapping):
        raise WaitRegistryError("wait record mapping field keys must be strings")
    return {key: item for key, item in mapping.items() if isinstance(key, str)}
