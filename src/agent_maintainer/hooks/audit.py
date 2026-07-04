"""Append local JSONL audit records for agent hook executions."""

from __future__ import annotations

import json
import os
import time
import tomllib
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from agent_maintainer.core.runtime import hardened_subprocess_env

DEFAULT_LOG_DIR = ".verify-logs"
HOOK_AUDIT_NAME = "hooks.jsonl"


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
    platform: str = "codex"
    reason: str = ""

    def to_payload(self) -> dict[str, object]:
        """Return a stable JSON payload for the audit log."""

        payload: dict[str, object] = {
            "version": 1,
            "timestamp": self.ended_at,
            "platform": self.platform,
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


def monotonic_timestamp() -> float:
    """Return monotonic timestamp for hook duration calculations."""

    return time.monotonic()


def duration_since(started_at: float) -> float:
    """Return elapsed seconds from a monotonic timestamp."""

    return round(time.monotonic() - started_at, 3)


def status_for_exit(exit_code: int | None) -> str:
    """Return audit status for a subprocess exit code."""

    return "passed" if exit_code == 0 else "failed"


def record_hook_result(repo_root: Path, record: HookAuditRecord) -> None:
    """Append one hook audit record, ignoring audit-write failures."""

    audit_path = audit_file_path(repo_root)
    with suppress(OSError):
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        with audit_path.open("a", encoding="utf-8") as stream:
            json.dump(record.to_payload(), stream, sort_keys=True)
            stream.write("\n")


def audit_file_path(repo_root: Path) -> Path:
    """Return the configured hook-audit path for a repository."""

    return repo_root / configured_log_dir(repo_root) / HOOK_AUDIT_NAME


def configured_log_dir(repo_root: Path) -> str:
    """Return diagnostics log directory from pyproject, if configured."""

    pyproject_path = repo_root / "pyproject.toml"
    with suppress(OSError, tomllib.TOMLDecodeError):
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        diagnostics = data.get("tool", {}).get("agent_maintainer", {}).get("diagnostics", {})
        log_dir = diagnostics.get("log_dir")
        if isinstance(log_dir, str) and log_dir:
            return log_dir
    return DEFAULT_LOG_DIR


def hook_env_with_src(repo_root: Path) -> dict[str, str]:
    """Return hook subprocess environment with the local package importable."""

    env = hardened_subprocess_env()
    src_path = str(repo_root / "src")
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = f"{src_path}{os.pathsep}{pythonpath}" if pythonpath else src_path
    return env
