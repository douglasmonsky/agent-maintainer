"""Retained verifier run history helpers."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from agent_maintainer.models import CheckResult

RUNS_DIR_NAME = "runs"
RUN_ID_DIGEST_LENGTH = 12


@dataclass(frozen=True)
class SnapshotArtifacts:
    """Paths and overrides for one retained run snapshot."""

    failure_snapshot: Path | None
    log_path_overrides: dict[str, str]
    context_log_dir: str


def build_run_id(profile: str, fingerprint: Mapping[str, object] | None = None) -> str:
    """Return a human-readable identifier for one verifier run."""

    timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%S%fZ")
    digest = run_digest(fingerprint or {"profile": profile})
    return f"{timestamp}-{slug(profile)}-{digest}"


def run_digest(payload: Mapping[str, object]) -> str:
    """Return a short digest for a run identity payload."""

    raw = json.dumps(payload, sort_keys=True, default=str).encode()
    return hashlib.sha256(raw).hexdigest()[:RUN_ID_DIGEST_LENGTH]


def slug(value: str) -> str:
    """Return a conservative slug for artifact path components."""

    cleaned = "".join(character if character.isalnum() else "-" for character in value)
    return cleaned.strip("-").lower() or "verify"


def run_snapshot_dir(log_dir: Path, run_id: str) -> Path:
    """Return run-scoped artifact directory."""

    return log_dir / RUNS_DIR_NAME / run_id


def path_text(path: Path | None, repo_root: Path) -> str:
    """Return repo-relative path text when possible."""

    if path is None:
        return ""
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def prune_run_history(log_dir: Path, keep: int) -> None:
    """Remove older run snapshots beyond configured retention."""

    runs_dir = log_dir / RUNS_DIR_NAME
    if keep <= 0:
        shutil.rmtree(runs_dir, ignore_errors=True)
        return
    if not runs_dir.exists():
        return
    snapshots = sorted(
        (path for path in runs_dir.iterdir() if path.is_dir()),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
        reverse=True,
    )
    for snapshot in snapshots[keep:]:
        shutil.rmtree(snapshot, ignore_errors=True)


def atomic_write_text(path: Path, text: str) -> None:
    """Replace artifact text atomically after writing a temp sibling."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temp_file:
        temp_file.write(text if text.endswith("\n") else f"{text}\n")
        temp_path = Path(temp_file.name)
    temp_path.replace(path)


def copy_run_logs(
    snapshot_dir: Path,
    repo_root: Path,
    results: list[CheckResult],
) -> dict[str, str]:
    """Copy check logs into the run-scoped snapshot directory."""

    snapshot_dir.mkdir(parents=True, exist_ok=True)
    copied: dict[str, str] = {}
    for result in results:
        source = resolve_path(result.log_path, repo_root)
        if source is None or not source.exists():
            continue
        destination = snapshot_dir / f"{slug(result.name)}.log"
        if not same_path(source, destination):
            shutil.copyfile(source, destination)
        copied[result.name] = path_text(destination, repo_root)
    return copied


def same_path(left: Path, right: Path) -> bool:
    """Return whether two paths point to the same filesystem location."""

    try:
        return left.resolve() == right.resolve()
    except OSError:
        return False


def resolve_path(raw_path: str, repo_root: Path) -> Path | None:
    """Return an absolute path for artifact text when available."""

    if not raw_path:
        return None
    path = Path(raw_path)
    return path if path.is_absolute() else repo_root / path
