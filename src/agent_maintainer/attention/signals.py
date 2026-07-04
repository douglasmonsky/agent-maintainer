"""Collect deterministic attention signal inputs."""

from __future__ import annotations

import json
import os
import subprocess  # nosec B404
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from agent_maintainer.runtime_events.read import read_runtime_events

IGNORED_PARTS = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        ".verify-logs",
        "__pycache__",
        "build",
        "dist",
        "htmlcov",
        "mutants",
        "node_modules",
        "venv",
    },
)

PATH_KEYS = frozenset(
    {
        "artifact",
        "artifact_path",
        "file",
        "filename",
        "log_path",
        "manifest_path",
        "path",
        "source",
        "target",
        "target_path",
    },
)


def tracked_files(repo_root: Path) -> tuple[str, ...]:
    """Return deterministic repository file list."""
    git_files = _git_lines(repo_root, ("ls-files",))
    if git_files:
        untracked = _git_lines(repo_root, ("ls-files", "--others", "--exclude-standard"))
        return tuple(
            sorted({path for path in (*git_files, *untracked) if _is_attention_path(path)})
        )
    paths: list[str] = []
    for current, dirs, files in os.walk(repo_root):
        dirs[:] = [name for name in dirs if name not in IGNORED_PARTS]
        current_path = Path(current)
        for filename in files:
            path = current_path / filename
            relative = path.relative_to(repo_root).as_posix()
            if _is_attention_path(relative):
                paths.append(relative)
    return tuple(sorted(paths))


def changed_counts(repo_root: Path) -> Counter[str]:
    """Return currently changed file counts."""
    counts: Counter[str] = Counter()
    for path in _git_lines(repo_root, ("diff", "--name-only", "HEAD")):
        if _is_attention_path(path):
            counts[path] += 1
    for path in _git_lines(repo_root, ("diff", "--cached", "--name-only")):
        if _is_attention_path(path):
            counts[path] += 1
    for path in _git_lines(repo_root, ("ls-files", "--others", "--exclude-standard")):
        if _is_attention_path(path):
            counts[path] += 1
    return counts


def churn_counts(repo_root: Path, *, commit_limit: int = 40) -> Counter[str]:
    """Return recent committed file churn counts."""
    counts: Counter[str] = Counter()
    args = ("log", f"--max-count={commit_limit}", "--name-only", "--pretty=format:")
    for path in _git_lines(repo_root, args):
        if _is_attention_path(path):
            counts[path] += 1
    return counts


def runtime_event_counts(repo_root: Path, *, events_dir: Path) -> Counter[str]:
    """Return file mentions from runtime event artifacts."""
    result = read_runtime_events(events_dir)
    known = set(tracked_files(repo_root))
    counts: Counter[str] = Counter()
    for record in result.records:
        for path in _record_paths(record, repo_root=repo_root, known_paths=known):
            counts[path] += 1
    return counts


def verifier_artifact_counts(repo_root: Path, *, log_dir: Path) -> Counter[str]:
    """Return file mentions from verifier manifests."""
    known = set(tracked_files(repo_root))
    counts: Counter[str] = Counter()
    runs_dir = log_dir / "runs"
    if not runs_dir.exists():
        return counts
    for manifest_path in sorted(runs_dir.glob("*/manifest.json")):
        payload = _read_json(manifest_path)
        if payload is None:
            continue
        for path in _payload_paths(payload, repo_root=repo_root, known_paths=known):
            counts[path] += 1
    return counts


def docsync_counts(repo_root: Path) -> Counter[str]:
    """Return file mentions from DocSync trace and report artifacts."""
    paths = tracked_files(repo_root)
    counts: Counter[str] = Counter()
    for artifact in (
        repo_root / ".docsync" / "trace.yml",
        repo_root / ".docsync" / "out" / "report.json",
    ):
        if not artifact.exists():
            continue
        try:
            text = artifact.read_text(encoding="utf-8")
        except OSError:
            continue
        for path in paths:
            if path in text:
                counts[path] += text.count(path)
    return counts


def file_baseline_counts(repo_root: Path, *, log_dir: Path) -> Counter[str]:
    """Return file mentions from file-baseline artifacts when present."""
    known = set(tracked_files(repo_root))
    counts: Counter[str] = Counter()
    for artifact in (
        log_dir / "file-baselines.json",
        log_dir / "file-baseline.json",
        log_dir / "file-baselines" / "report.json",
    ):
        payload = _read_json(artifact)
        if payload is None:
            continue
        for path in _payload_paths(payload, repo_root=repo_root, known_paths=known):
            counts[path] += 1
    return counts


def path_heuristic_score(path: str) -> float:
    """Return deterministic path-priority score."""
    if path in {"README.md", "AGENTS.md", "AGENTS.agent-maintainer.md", "pyproject.toml"}:
        return 0.75
    prefixes = (
        ("src/", 0.55),
        ((".github/", ".codex/", ".claude/", "config/"), 0.5),
        ("docs/roadmap/", 0.4),
        ("docs/", 0.35),
        ("tests/", 0.3),
        ("examples/", 0.25),
    )
    for prefix, score in prefixes:
        if path.startswith(prefix):
            return score
    return 0.15


def _git_lines(repo_root: Path, args: tuple[str, ...]) -> tuple[str, ...]:
    """Run git and return non-empty stdout lines."""
    try:
        result = subprocess.run(
            ("git", *args),
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ()
    if result.returncode != 0:
        return ()
    return tuple(line.strip() for line in result.stdout.splitlines() if line.strip())


def _is_attention_path(path: str) -> bool:
    """Return whether path is useful source attention target."""
    path_obj = Path(path)
    if path_obj.is_absolute() or ".." in path_obj.parts:
        return False
    return not IGNORED_PARTS.intersection(path_obj.parts)


def _record_paths(
    record: Mapping[str, Any],
    *,
    repo_root: Path,
    known_paths: set[str],
) -> tuple[str, ...]:
    """Extract known repo file paths from a runtime event record."""
    return tuple(_payload_paths(record, repo_root=repo_root, known_paths=known_paths))


def _payload_paths(
    payload: object,
    *,
    repo_root: Path,
    known_paths: set[str],
) -> set[str]:
    """Extract known repo file paths from nested JSON-like payload."""
    found: set[str] = set()
    for key, value in _walk_values(payload):
        if isinstance(value, str):
            found.update(
                _match_known_path(
                    value,
                    key=key,
                    repo_root=repo_root,
                    known_paths=known_paths,
                )
            )
    return found


def _walk_values(payload: object) -> Iterable[tuple[str | None, object]]:
    """Yield nested mapping keys and scalar values."""
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            key_text = str(key)
            yield key_text, value
            yield from _walk_values(value)
    elif isinstance(payload, list | tuple):
        for value in payload:
            yield None, value
            yield from _walk_values(value)


def _match_known_path(
    value: str,
    *,
    key: str | None,
    repo_root: Path,
    known_paths: set[str],
) -> set[str]:
    """Return known repo paths represented by one string value."""
    candidates = {value}
    if key in PATH_KEYS:
        candidates.add(_relative_text(value, repo_root=repo_root))
    matches = {candidate for candidate in candidates if candidate in known_paths}
    if matches:
        return matches
    if key in PATH_KEYS:
        return set()
    return {path for path in known_paths if path in value}


def _relative_text(value: str, *, repo_root: Path) -> str:
    """Return repository-relative text when value is an in-repo path."""
    path = Path(value)
    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return value


def _read_json(path: Path) -> object | None:
    """Read JSON artifact if present and valid."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
