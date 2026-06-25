"""Doctor checks for Codex hook audit records."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import guardrail_config
from scripts.guardrail_doctor_models import OK, WARNING, DoctorResult

HOOK_AUDIT_NAME = "hooks.jsonl"
VERIFY_LOG_DIR = ".verify-logs"
REQUIRED_FIELDS = frozenset(("timestamp", "hook", "profile", "status"))


def check_hook_audit(
    repo_root: Path, config: guardrail_config.GuardrailConfig | None = None
) -> DoctorResult:
    """Report whether Codex hook executions have a local audit trail."""

    if not codex_hooks_enabled(repo_root):
        return DoctorResult("hook-audit", OK, "Codex hooks are not enabled; audit not required.")
    log_dir_name = config.diagnostic_artifacts_dir if config else VERIFY_LOG_DIR
    audit_path = repo_root / log_dir_name / HOOK_AUDIT_NAME
    if not audit_path.exists():
        return DoctorResult(
            "hook-audit", WARNING, f"{audit_path.relative_to(repo_root)} is absent."
        )
    event = latest_hook_event(audit_path)
    if event is None:
        return DoctorResult("hook-audit", WARNING, f"{HOOK_AUDIT_NAME} has no valid events.")
    return hook_audit_result(event)


def codex_hooks_enabled(repo_root: Path) -> bool:
    """Return whether repo-local Codex hooks are enabled."""

    config_path = repo_root / ".codex" / "config.toml"
    return config_path.exists() and "hooks = true" in config_path.read_text(encoding="utf-8")


def latest_hook_event(audit_path: Path) -> dict[str, object] | None:
    """Return the latest JSONL hook audit event."""

    try:
        lines = audit_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        if line.strip():
            return read_hook_event(line)
    return None


def read_hook_event(line: str) -> dict[str, object] | None:
    """Read one hook audit JSONL line."""

    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def hook_audit_result(event: dict[str, object]) -> DoctorResult:
    """Return the doctor result for the latest hook event."""

    missing = REQUIRED_FIELDS.difference(event)
    if missing:
        missing_names = ", ".join(sorted(missing))
        return DoctorResult("hook-audit", WARNING, f"{HOOK_AUDIT_NAME} missing: {missing_names}")
    if event.get("status") != "passed":
        return DoctorResult("hook-audit", WARNING, hook_event_summary(event))
    return DoctorResult("hook-audit", OK, hook_event_summary(event))


def hook_event_summary(event: dict[str, object]) -> str:
    """Return a compact latest-hook summary for doctor output."""

    hook = event.get("hook", "unknown hook")
    status = event.get("status", "unknown status")
    profile = event.get("profile", "unknown profile")
    timestamp = event.get("timestamp", "unknown time")
    return f"Latest hook audit: {hook} {status} for {profile} at {timestamp}"
