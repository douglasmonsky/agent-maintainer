"""Tests verifier run locking."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from agent_maintainer.verify.locking import LOCK_NAME, VerificationFingerprint, VerificationLock


def fingerprint() -> VerificationFingerprint:
    """Return a stable test fingerprint."""

    return VerificationFingerprint(
        profile="fast",
        base_ref="HEAD",
        compare_branch="origin/main",
        staged=False,
        head="abc123",
        index_hash="index",
        worktree_hash="worktree",
        config_hash="config",
    )


def test_verification_lock_reuses_completed_same_state_result(tmp_path: Path) -> None:
    """Same-state overlapping verification can point at the prior result."""

    log_dir = tmp_path / ".verify-logs"
    current = fingerprint()

    with VerificationLock(log_dir=log_dir, fingerprint=current) as lock:
        assert lock.reused is None
        assert (log_dir / LOCK_NAME).exists()
        lock.write_result(0)

    with VerificationLock(log_dir=log_dir, fingerprint=current) as lock:
        assert lock.reused is not None
        assert lock.reused.exit_code == 0
        assert not (log_dir / LOCK_NAME).exists()


def test_verification_lock_does_not_reuse_different_repo_state(tmp_path: Path) -> None:
    """A changed repo fingerprint must run fresh instead of reusing old output."""

    log_dir = tmp_path / ".verify-logs"
    current = fingerprint()
    changed = replace(current, worktree_hash="changed")

    with VerificationLock(log_dir=log_dir, fingerprint=current) as lock:
        lock.write_result(0)

    with VerificationLock(log_dir=log_dir, fingerprint=changed) as lock:
        assert lock.reused is None
        assert (log_dir / LOCK_NAME).exists()
