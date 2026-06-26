"""Doctor checks for Codex hook audit records."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ai_guardrails.core import config as guardrail_config
from ai_guardrails.doctor.support.models import OK, WARNING, DoctorResult

HOOK_AUDIT_NAME = "hooks.jsonl"
VERIFY_LOG_DIR = ".verify-logs"
REQUIRED_FIELDS = frozenset(("timestamp", "hook", "profile", "status"))
STALE_AFTER_HOURS = 48
STALE_AFTER = timedelta(hours=STALE_AFTER_HOURS)
HookEvent = Mapping[str, object]


def check_hook_audit(
    repo_root: Path,
    config: guardrail_config.GuardrailConfig | None = None,
    *,
    now: datetime | None = None,
) -> DoctorResult:
    """Report Codex hook executions from the local audit trail."""

    if not codex_hooks_enabled(repo_root):
        return DoctorResult("hook-audit", OK, "Codex hooks not enabled; audit not required.")
    log_dir_name = config.diagnostic_artifacts_dir if config else VERIFY_LOG_DIR
    audit_path = repo_root / log_dir_name / HOOK_AUDIT_NAME
    if not audit_path.exists():
        return DoctorResult(
            "hook-audit", WARNING, f"{audit_path.relative_to(repo_root)} is absent."
        )
    events, malformed_count = valid_hook_events(audit_path)
    if not events:
        return no_valid_events_result(malformed_count)
    return hook_audit_result(events[-1], malformed_count, now=now)


def codex_hooks_enabled(repo_root: Path) -> bool:
    """Return whether repo-local Codex hooks are enabled."""

    config_path = repo_root / ".codex" / "config.toml"
    return config_path.exists() and "hooks = true" in config_path.read_text(encoding="utf-8")


def valid_hook_events(audit_path: Path) -> tuple[list[HookEvent], int]:
    """Return valid hook audit events and malformed entry count."""

    try:
        lines = audit_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return [], 1
    valid_events: list[HookEvent] = []
    malformed_count = 0
    for line in lines:
        if not line.strip():
            continue
        event = parse_hook_event(line)
        if event is None:
            malformed_count += 1
        else:
            valid_events.append(event)
    return valid_events, malformed_count


def parse_hook_event(line: str) -> HookEvent | None:
    """Parse one hook audit JSONL event when it has required fields."""

    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    if missing_required_fields(payload):
        return None
    if event_timestamp(payload) is None:
        return None
    return payload


def missing_required_fields(event: HookEvent) -> list[str]:
    """Return missing required hook audit fields."""

    return sorted(field for field in REQUIRED_FIELDS if field not in event)


def event_timestamp(event: HookEvent) -> datetime | None:
    """Return parsed hook event timestamp."""

    value = event.get("timestamp")
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def no_valid_events_result(malformed_count: int) -> DoctorResult:
    """Return warning for audit logs with no usable hook events."""

    if malformed_count:
        return DoctorResult(
            "hook-audit",
            WARNING,
            f"{HOOK_AUDIT_NAME} has no valid events; malformed={malformed_count}.",
        )
    return DoctorResult("hook-audit", WARNING, f"{HOOK_AUDIT_NAME} has no valid events.")


def hook_audit_result(
    event: HookEvent,
    malformed_count: int = 0,
    *,
    now: datetime | None = None,
) -> DoctorResult:
    """Return doctor status for the latest valid hook audit event."""

    timestamp = event_timestamp(event)
    if timestamp is None:
        return no_valid_events_result(malformed_count + 1)
    current_time = now or datetime.now(tz=UTC)
    if current_time - timestamp > STALE_AFTER:
        return DoctorResult(
            "hook-audit",
            WARNING,
            f"Latest hook audit is stale: {hook_event_summary(event)}.",
        )
    status = event.get("status")
    if status != "passed":
        return DoctorResult(
            "hook-audit",
            WARNING,
            f"Latest hook audit did not pass: {hook_event_summary(event)}.",
        )
    return DoctorResult("hook-audit", OK, hook_event_summary(event, malformed_count))


def hook_event_summary(event: HookEvent, malformed_count: int = 0) -> str:
    """Return latest-hook summary for doctor output."""

    hook = event.get("hook", "unknown hook")
    status = event.get("status", "unknown status")
    profile = event.get("profile", "unknown profile")
    timestamp = event.get("timestamp", "unknown time")
    summary = f"Latest hook audit: {hook} {status} for {profile} at {timestamp}"
    if malformed_count:
        summary = f"{summary}; ignored malformed={malformed_count}"
    return summary
