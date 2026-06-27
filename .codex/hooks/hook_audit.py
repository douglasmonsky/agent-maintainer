"""Append local JSONL audit records for Codex hook executions."""

from __future__ import annotations

import json
import os
import time
import tomllib
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_LOG_DIR = ".verify-logs"
HOOK_AUDIT_NAME = "hooks.jsonl"
ALLOW_BYTECODE_ENV = "AGENT_MAINTAINER_WRITE_BYTECODE"
PYTHON_BYTECODE_ENV = "PYTHONDONTWRITEBYTECODE"
TRUE_ENV_VALUES = frozenset(("1", "true", "yes", "on"))


@dataclass(frozen=True)
class HookAuditRecord:
    """One local hook execution record."""

    hook_name: str
    profile: str
    status: str
    command: tuple[str, ...]
    exit_code: int | None
    started_at: str
    ended_at: str
    duration_seconds: float
    reason: str = ""

    def to_payload(self) -> dict[str, object]:
        """Return a stable JSON payload for the audit log."""

        payload: dict[str, object] = {
            "version": 1,
            "timestamp": self.ended_at,
            "hook": self.hook_name,
            "profile": self.profile,
            "status": self.status,
            "command": list(self.command),
            "exit_code": self.exit_code,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_seconds": self.duration_seconds,
        }
        if self.reason:
            payload["reason"] = self.reason
        return payload


def utc_timestamp() -> str:
    """Return a stable UTC timestamp for hook audit records."""

    return datetime.now(tz=UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def duration_since(started: float) -> float:
    """Return elapsed monotonic time rounded for compact JSONL output."""

    return round(time.monotonic() - started, 3)


def status_for_exit(exit_code: int | None) -> str:
    """Return the audit status for a verifier exit code."""

    return "passed" if exit_code == 0 else "failed"


def hardened_subprocess_env() -> dict[str, str]:
    """Return hook subprocess environment with bytecode writes disabled by default."""
    environment = os.environ.copy()
    if environment.get(ALLOW_BYTECODE_ENV, "").casefold() in TRUE_ENV_VALUES:
        environment.pop(PYTHON_BYTECODE_ENV, None)
    else:
        environment[PYTHON_BYTECODE_ENV] = "1"
    return environment


def hook_audit_path(repo_root: Path) -> Path:
    """Return the audit JSONL path for a repository."""

    return diagnostic_log_dir(repo_root) / HOOK_AUDIT_NAME


def diagnostic_log_dir(repo_root: Path) -> Path:
    """Return the configured diagnostics directory, falling back safely."""

    config_path = repo_root / "pyproject.toml"
    if not config_path.exists():
        return repo_root / DEFAULT_LOG_DIR
    try:
        payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return repo_root / DEFAULT_LOG_DIR
    log_dir = (
        payload.get("tool", {}).get("agent_maintainer", {}).get("diagnostics", {}).get("log_dir")
    )
    if isinstance(log_dir, str) and log_dir:
        return repo_root / log_dir
    return repo_root / DEFAULT_LOG_DIR


def record_hook_result(repo_root: Path, record: HookAuditRecord) -> None:
    """Append a hook audit record without masking verifier behavior."""

    with suppress(OSError):
        append_payload(hook_audit_path(repo_root), record.to_payload())


def append_payload(path: Path, payload: dict[str, object]) -> None:
    """Append one JSON payload to a JSONL file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{json.dumps(payload, sort_keys=True)}\n")
