"""State-aware verifier run locking."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import subprocess  # nosec B404
import time
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Self

LOCK_NAME = "agent-maintainer.lock"
RESULT_NAME = "agent-maintainer-last-result.json"
LOCK_STALE_MINUTES = 20
SECONDS_PER_MINUTE = 60
LOCK_STALE_SECONDS = LOCK_STALE_MINUTES * SECONDS_PER_MINUTE
LOCK_WAIT_SECONDS = 45.0
LOCK_POLL_SECONDS = 0.25
CONFIG_FINGERPRINT_PATHS = (
    "pyproject.toml",
    "tach.toml",
    ".pre-commit-config.yaml",
    ".github/dependabot.yml",
    ".github/workflows/verify.yml",
    "semgrep.yml",
    "osv-scanner.toml",
    "config/dev-dependencies.txt",
    "config/dev-lock.txt",
    "package.json",
    "package-lock.json",
)


@dataclass(frozen=True)
class VerificationFingerprint:
    """Repository state identity for one verifier request."""

    profile: str
    base_ref: str
    compare_branch: str
    staged: bool
    head: str
    index_hash: str
    worktree_hash: str
    config_hash: str

    def to_dict(self) -> dict[str, object]:
        """Return JSON-serializable fingerprint payload."""

        return {
            "profile": self.profile,
            "base_ref": self.base_ref,
            "compare_branch": self.compare_branch,
            "staged": self.staged,
            "head": self.head,
            "index_hash": self.index_hash,
            "worktree_hash": self.worktree_hash,
            "config_hash": self.config_hash,
        }


@dataclass(frozen=True)
class ReusedVerification:
    """Previously completed verification result for the same repo state."""

    exit_code: int


class VerificationLock:
    """Exclusive verifier lock with same-state result reuse."""

    def __init__(
        self,
        *,
        log_dir: Path,
        fingerprint: VerificationFingerprint,
        wait_seconds: float = LOCK_WAIT_SECONDS,
    ) -> None:
        self._log_dir = log_dir
        self._fingerprint = fingerprint
        self._wait_seconds = wait_seconds
        self._lock_path = log_dir / LOCK_NAME
        self._result_path = log_dir / RESULT_NAME
        self._acquired = False
        self.reused: ReusedVerification | None = None

    def __enter__(self) -> Self:
        """Acquire lock or reuse same-state completed result."""

        self._log_dir.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + self._wait_seconds
        while True:
            reused = self.reusable_result()
            if reused is not None:
                self.reused = reused
                return self

            if self.try_acquire():
                self._acquired = True
                return self

            self.break_stale_lock()
            if time.monotonic() >= deadline:
                raise TimeoutError("another Agent Maintainer verification is still running")
            time.sleep(LOCK_POLL_SECONDS)

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        """Release lock when this process acquired it."""

        if self._acquired:
            with contextlib.suppress(OSError):
                self._lock_path.unlink()

    def try_acquire(self) -> bool:
        """Try to atomically create the lock file."""

        payload = {
            "pid": os.getpid(),
            "created_at": time.time(),
            "fingerprint": self._fingerprint.to_dict(),
        }
        try:
            fd = os.open(self._lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True)
            handle.write("\n")
        return True

    def reusable_result(self) -> ReusedVerification | None:
        """Return completed same-state result when available."""

        try:
            payload = json.loads(self._result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if payload.get("fingerprint") != self._fingerprint.to_dict():
            return None
        exit_code = payload.get("exit_code")
        if not isinstance(exit_code, int):
            return None
        if self._lock_path.exists():
            return None
        return ReusedVerification(exit_code=exit_code)

    def break_stale_lock(self) -> None:
        """Remove lock files older than the stale threshold."""

        with contextlib.suppress(OSError):
            age = time.time() - self._lock_path.stat().st_mtime
            if age > LOCK_STALE_SECONDS:
                self._lock_path.unlink()

    def write_result(self, exit_code: int) -> None:
        """Persist completed verification result for same-state reuse."""

        payload = {
            "fingerprint": self._fingerprint.to_dict(),
            "exit_code": exit_code,
            "completed_at": time.time(),
        }
        result_text = f"{json.dumps(payload, sort_keys=True)}\n"
        self._result_path.write_text(result_text, encoding="utf-8")


def build_fingerprint(
    *,
    repo_root: Path,
    profile: str,
    base_ref: str,
    compare_branch: str,
    staged: bool,
) -> VerificationFingerprint:
    """Return repository state fingerprint for verification reuse."""

    return VerificationFingerprint(
        profile=profile,
        base_ref=base_ref,
        compare_branch=compare_branch,
        staged=staged,
        head=git_output(repo_root, "rev-parse", "HEAD"),
        index_hash=git_hash(repo_root, "diff", "--cached", "--binary"),
        worktree_hash=git_hash(repo_root, "diff", "--binary"),
        config_hash=files_hash(repo_root, CONFIG_FINGERPRINT_PATHS),
    )


def git_hash(repo_root: Path, *args: str) -> str:
    """Return stable hash for Git command output."""

    output = git_output(repo_root, *args)
    return hashlib.sha256(output.encode()).hexdigest()


def git_output(repo_root: Path, *args: str) -> str:
    """Return Git stdout or an empty string when Git is unavailable."""

    git_path = shutil.which("git")
    if git_path is None:
        return ""
    result = subprocess.run(  # nosec B603
        [git_path, *args],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout


def file_hash(path: Path) -> str:
    """Return stable hash for one file."""

    try:
        content = path.read_bytes()
    except OSError:
        content = b""
    return hashlib.sha256(content).hexdigest()


def files_hash(repo_root: Path, paths: tuple[str, ...]) -> str:
    """Return stable hash of verifier-relevant config files."""

    digest = hashlib.sha256()
    for relative_path in paths:
        path = repo_root / relative_path
        digest.update(relative_path.encode())
        digest.update(b"\0")
        digest.update(file_hash(path).encode())
        digest.update(b"\0")
    return digest.hexdigest()
