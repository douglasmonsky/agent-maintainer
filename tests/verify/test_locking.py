"""Tests verifier run locking."""

from __future__ import annotations

import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from agent_maintainer.verify import fingerprint_inputs
from agent_maintainer.verify.fingerprint_inputs import (
    CONFIG_FINGERPRINT_PATHS,
    environment_hash,
    files_hash,
    untracked_files_hash,
)
from agent_maintainer.verify.locking import (
    LOCK_NAME,
    VerificationFingerprint,
    VerificationLock,
    build_fingerprint,
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
        environment_hash="environment",
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


def test_lock_reuse_invalidates_every_execution_identity_component(tmp_path: Path) -> None:
    """Refs, inputs, configuration, and environment each invalidate reuse."""

    current = fingerprint()
    changed_states = (
        replace(current, base_ref="other"),
        replace(current, index_hash="other"),
        replace(current, worktree_hash="other"),
        replace(current, untracked_hash="other"),
        replace(current, config_hash="other"),
        replace(current, environment_hash="other"),
    )
    for index, changed in enumerate(changed_states):
        log_dir = tmp_path / str(index)
        with VerificationLock(log_dir=log_dir, fingerprint=current) as lock:
            lock.write_result(0)
        with VerificationLock(log_dir=log_dir, fingerprint=changed) as lock:
            assert lock.reused is None


def test_lock_does_not_reuse_another_verification_group(tmp_path: Path) -> None:
    """Each partial group has a distinct same-state reuse identity."""

    log_dir = tmp_path / ".verify-logs"
    tests_group = replace(fingerprint(), group="tests-and-coverage")
    static_group = replace(fingerprint(), group="static-and-policy")

    with VerificationLock(log_dir=log_dir, fingerprint=tests_group) as lock:
        lock.write_result(0)

    with VerificationLock(log_dir=log_dir, fingerprint=static_group) as lock:
        assert lock.reused is None


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


def test_environment_hash_tracks_tool_resolution_and_maintainer_overrides() -> None:
    """Reuse cannot cross Python/tool paths or Agent Maintainer environment modes."""

    base = {"PATH": "/tools/one", "PYTHONPATH": "src", "VIRTUAL_ENV": "/venv"}

    assert environment_hash(base) != environment_hash({**base, "PATH": "/tools/two"})
    assert environment_hash(base) != environment_hash(
        {**base, "AGENT_MAINTAINER_ENABLE_PIP_AUDIT": "1"}
    )


def test_build_fingerprint_normalizes_git_head(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Git's line terminator must not become part of the commit identity."""

    monkeypatch.setattr(
        fingerprint_inputs,
        "git_output",
        lambda *_args: "abc123\n",
    )
    monkeypatch.setattr(fingerprint_inputs, "git_hash", lambda *_args: "hash")
    monkeypatch.setattr(fingerprint_inputs, "untracked_files_hash", lambda _root: "untracked")
    monkeypatch.setattr(fingerprint_inputs, "files_hash", lambda *_args: "config")
    monkeypatch.setattr(fingerprint_inputs, "environment_hash", lambda _env: "environment")

    current = build_fingerprint(
        repo_root=tmp_path,
        profile="ci",
        base_ref="origin/main",
        compare_branch="origin/main",
        staged=False,
    )

    assert current.head == "abc123"


@pytest.mark.parametrize("changed_path", ("src/example.py", "tests/test_example.py"))
def test_build_fingerprint_tracks_staged_source_and_test_changes(
    tmp_path: Path, changed_path: str
) -> None:
    """The index identity changes for staged source and test edits."""

    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    path = tmp_path / changed_path
    path.parent.mkdir(parents=True)
    path.write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", changed_path], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Agent",
            "-c",
            "user.email=agent@example.invalid",
            "commit",
            "-m",
            "initial",
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    before = build_fingerprint(
        repo_root=tmp_path,
        profile="fast",
        base_ref="HEAD",
        compare_branch="origin/main",
        staged=True,
    )
    path.write_text("VALUE = 2\n", encoding="utf-8")
    subprocess.run(["git", "add", changed_path], cwd=tmp_path, check=True, capture_output=True)

    after = build_fingerprint(
        repo_root=tmp_path,
        profile="fast",
        base_ref="HEAD",
        compare_branch="origin/main",
        staged=True,
    )

    assert before.index_hash != after.index_hash
