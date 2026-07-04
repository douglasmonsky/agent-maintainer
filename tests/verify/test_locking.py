"""Tests verifier run locking."""

from __future__ import annotations

import subprocess
from dataclasses import replace
from pathlib import Path

from agent_maintainer.verify.locking import (
    CONFIG_FINGERPRINT_PATHS,
    LOCK_NAME,
    VerificationFingerprint,
    VerificationLock,
    files_hash,
    untracked_files_hash,
)


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
        untracked_hash="untracked",
        config_hash="config",
    )


def test_lock_reuses_same_state_result(tmp_path: Path) -> None:
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


def test_lock_reused_result_includes_run_id(tmp_path: Path) -> None:
    """Same-state completed result retains verifier run id."""
    log_dir = tmp_path / ".verify-logs"
    current = fingerprint()

    with VerificationLock(log_dir=log_dir, fingerprint=current, run_id="run-1") as lock:
        lock.write_result(1)

    with VerificationLock(log_dir=log_dir, fingerprint=current) as lock:
        assert lock.reused is not None
        assert lock.reused.exit_code == 1
        assert lock.reused.run_id == "run-1"


def test_lock_force_skips_same_state_result(tmp_path: Path) -> None:
    """Forced verification bypasses completed same-state result reuse."""

    log_dir = tmp_path / ".verify-logs"
    current = fingerprint()
    with VerificationLock(log_dir=log_dir, fingerprint=current) as lock:
        lock.write_result(0)

    with VerificationLock(
        log_dir=log_dir,
        fingerprint=current,
        reuse_result=False,
    ) as lock:
        assert lock.reused is None
        assert (log_dir / LOCK_NAME).exists()


def test_lock_skips_changed_repo_state(tmp_path: Path) -> None:
    """A changed repo fingerprint must run fresh instead of reusing old output."""

    log_dir = tmp_path / ".verify-logs"
    current = fingerprint()
    changed = replace(current, worktree_hash="changed")

    with VerificationLock(log_dir=log_dir, fingerprint=current) as lock:
        lock.write_result(0)

    with VerificationLock(log_dir=log_dir, fingerprint=changed) as lock:
        assert lock.reused is None
        assert (log_dir / LOCK_NAME).exists()


def test_untracked_hash_changes(tmp_path: Path) -> None:
    """Untracked source files must affect verifier reuse identity."""

    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    before = untracked_files_hash(tmp_path)

    source = tmp_path / "src" / "example.py"
    source.parent.mkdir()
    source.write_text("VALUE = 1\n", encoding="utf-8")
    after = untracked_files_hash(tmp_path)

    source.write_text("VALUE = 2\n", encoding="utf-8")
    changed = untracked_files_hash(tmp_path)

    assert before != after
    assert after != changed


def test_config_hash_includes_tool_config(tmp_path: Path) -> None:
    """Changing a verifier-adjacent config file changes reuse fingerprint."""

    (tmp_path / "pyproject.toml").write_text("[tool.agent_maintainer]\n", encoding="utf-8")
    (tmp_path / "tach.toml").write_text("root_module = 'forbid'\n", encoding="utf-8")
    before = files_hash(tmp_path, CONFIG_FINGERPRINT_PATHS)

    (tmp_path / "tach.toml").write_text("root_module = 'ignore'\n", encoding="utf-8")
    after = files_hash(tmp_path, CONFIG_FINGERPRINT_PATHS)

    assert before != after
