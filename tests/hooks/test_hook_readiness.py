"""Tests hook-visible verifier readiness."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from agent_maintainer.hooks import readiness
from agent_maintainer.verify.locking import LOCK_NAME, RESULT_NAME, VerificationFingerprint


def fingerprint(profile: str = "fast") -> VerificationFingerprint:
    """Return stable verifier fingerprint for readiness tests."""
    return VerificationFingerprint(
        profile=profile,
        base_ref="HEAD",
        compare_branch="origin/main",
        staged=False,
        head="head",
        index_hash="index",
        worktree_hash="worktree",
        untracked_hash="untracked",
        config_hash="config",
    )


def test_completed_readiness_uses_run_id(tmp_path: Path) -> None:
    """Completed same-state result exposes its verifier run id."""
    log_dir = tmp_path / ".verify-logs"
    log_dir.mkdir()
    current = fingerprint()
    (log_dir / RESULT_NAME).write_text(
        json.dumps(
            {
                "fingerprint": current.to_dict(),
                "exit_code": 1,
                "run_id": "run-fail",
            },
        ),
        encoding="utf-8",
    )

    result = readiness.completed_readiness(log_dir, current)

    assert result is not None
    assert result.completed
    assert result.run_id == "run-fail"
    assert "wait verifier run-fail" in readiness.render_hook_readiness(result)


def test_pending_readiness_requires_live_state(tmp_path: Path) -> None:
    """Pending readiness only reports same-state live verifier locks."""
    log_dir = tmp_path / ".verify-logs"
    log_dir.mkdir()
    current = fingerprint()
    (log_dir / LOCK_NAME).write_text(
        json.dumps(
            {
                "fingerprint": current.to_dict(),
                "pid": os.getpid(),
                "run_id": "run-pending",
                "created_at": time.time(),
            },
        ),
        encoding="utf-8",
    )

    result = readiness.pending_readiness(log_dir, current)

    assert result is not None
    assert result.pending
    assert result.run_id == "run-pending"


def test_pending_readiness_ignores_changed_state(tmp_path: Path) -> None:
    """Changed repo state does not reuse an in-flight verifier lock."""
    log_dir = tmp_path / ".verify-logs"
    log_dir.mkdir()
    current = fingerprint()
    changed = fingerprint(profile="precommit")
    (log_dir / LOCK_NAME).write_text(
        json.dumps(
            {
                "fingerprint": current.to_dict(),
                "pid": os.getpid(),
                "run_id": "run-pending",
            },
        ),
        encoding="utf-8",
    )

    assert readiness.pending_readiness(log_dir, changed) is None
