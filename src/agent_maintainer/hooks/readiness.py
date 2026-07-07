"""Hook-visible verifier readiness state."""

from __future__ import annotations

import contextlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from agent_maintainer.verify.locking import (
    LOCK_NAME,
    LOCK_STALE_SECONDS,
    RESULT_NAME,
    VerificationFingerprint,
    build_fingerprint,
)
from agent_waits.models import WaitRepairCapsule, render_wait_capsule

BASE_REF: Final = "HEAD"
COMPARE_BRANCH: Final = "origin/main"


@dataclass(frozen=True)
class HookExecution:
    """Shared metadata for one hook runtime execution."""

    repo_root: Path
    platform: str
    event: str
    profile: str
    started_at: str
    started: float
    runtime_events: Any


@dataclass(frozen=True)
class HookReadiness:
    """Same-state verifier result visible to agent hooks."""

    status: str
    profile: str
    run_id: str
    exit_code: int | None = None

    @property
    def passed(self) -> bool:
        """Return whether readiness represents a successful completed run."""
        return self.status == "completed" and self.exit_code == 0

    @property
    def completed(self) -> bool:
        """Return whether readiness represents completed verifier work."""
        return self.status == "completed"

    @property
    def pending(self) -> bool:
        """Return whether readiness represents in-flight verifier work."""
        return self.status == "pending"


def hook_readiness(repo_root: Path, profile: str) -> HookReadiness | None:
    """Return same-state completed or in-flight verifier state for hooks."""
    log_dir = repo_root / ".verify-logs"
    fingerprint = hook_fingerprint(repo_root, profile)
    completed = completed_readiness(log_dir, fingerprint)
    if completed is not None:
        return completed
    return pending_readiness(log_dir, fingerprint)


def hook_fingerprint(repo_root: Path, profile: str) -> VerificationFingerprint:
    """Return verifier fingerprint used by hook-triggered verification."""
    return build_fingerprint(
        repo_root=repo_root,
        profile=profile,
        base_ref=BASE_REF,
        compare_branch=os.getenv("COMPARE_BRANCH", COMPARE_BRANCH),
        staged=False,
    )


def completed_readiness(
    log_dir: Path,
    fingerprint: VerificationFingerprint,
) -> HookReadiness | None:
    """Return completed same-state verifier readiness if available."""
    if (log_dir / LOCK_NAME).exists():
        return None
    payload = _json_object(log_dir / RESULT_NAME)
    if payload.get("fingerprint") != fingerprint.to_dict():
        return None
    exit_code = payload.get("exit_code")
    if not isinstance(exit_code, int):
        return None
    return HookReadiness(
        status="completed",
        profile=fingerprint.profile,
        run_id=str(payload.get("run_id", "")),
        exit_code=exit_code,
    )


def pending_readiness(
    log_dir: Path,
    fingerprint: VerificationFingerprint,
) -> HookReadiness | None:
    """Return in-flight same-state verifier readiness if available."""
    payload = _json_object(log_dir / LOCK_NAME)
    if payload.get("fingerprint") != fingerprint.to_dict():
        return None
    if _stale_lock(log_dir / LOCK_NAME) or not _pid_alive(payload.get("pid")):
        return None
    return HookReadiness(
        status="pending",
        profile=fingerprint.profile,
        run_id=str(payload.get("run_id", "")),
    )


def render_hook_readiness(readiness: HookReadiness) -> str:
    """Render hook-visible readiness capsule."""
    if readiness.pending:
        return render_wait_capsule(
            WaitRepairCapsule(
                result="PENDING",
                profile=readiness.profile,
                run_id=readiness.run_id or "unknown",
                likely_next_action=_wait_command(readiness),
            ),
        )
    if readiness.passed:
        return render_wait_capsule(
            WaitRepairCapsule(
                result="PASS",
                profile=readiness.profile,
                run_id=readiness.run_id or "unknown",
            ),
        )
    return render_wait_capsule(
        WaitRepairCapsule(
            result="FAIL",
            profile=readiness.profile,
            run_id=readiness.run_id or "unknown",
            likely_next_action=_wait_command(readiness),
        ),
    )


def _wait_command(readiness: HookReadiness) -> str:
    if not readiness.run_id:
        return f"python -m agent_maintainer verify --profile {readiness.profile}"
    return f"python -m agent_maintainer wait verifier {readiness.run_id}"


def _json_object(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _stale_lock(path: Path) -> bool:
    with contextlib.suppress(OSError):
        return time.time() - path.stat().st_mtime > LOCK_STALE_SECONDS
    return True


def _pid_alive(pid_value: object) -> bool:
    if not isinstance(pid_value, int):
        return False
    with contextlib.suppress(OSError):
        os.kill(pid_value, 0)
        return True
    return False
