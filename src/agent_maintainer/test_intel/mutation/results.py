"""Render exported Mutmut result statistics."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from agent_maintainer.runners.mutmut_stats import (
    DEFAULT_STATS_PATH,
    MutmutStats,
    render_summary,
)
from agent_maintainer.runners.mutmut_stats import read_stats as read_mutmut_stats

LOG_DIR = Path(".verify-logs") / "runs"
SWEEP_LOG_DIR = Path(".verify-logs") / "mutation-sweeps"
MUTMUT_LOG_NAME = "mutmut.log"
MUTMUT_STATS_NAME = "mutmut-cicd-stats.json"
LIVE_SOURCE = "live"
RUN_ARTIFACT_SOURCE = "run-artifact"
RATCHET_SUMMARY_RE = re.compile(
    r"mutmut score (?P<score>\d+(?:\.\d+)?)% "
    r"\((?P<killed>\d+)/(?P<total>\d+) killed, "
    r"(?P<survived>\d+) survived, "
    r"(?P<suspicious>\d+) suspicious, "
    r"(?P<timeout>\d+) timeout\)",
)


@dataclass(frozen=True)
class MutationResultSource:
    """Mutation result stats with source metadata."""

    stats: MutmutStats
    kind: str
    path: Path


def read_stats(path: Path) -> MutmutStats:
    """Read exported Mutmut result statistics."""
    return read_mutmut_stats(path)


def read_result_source(path: Path = DEFAULT_STATS_PATH) -> MutationResultSource:
    """Read live Mutmut stats or the latest run-scoped artifact summary."""
    if path.exists():
        return MutationResultSource(
            stats=read_mutmut_stats(path),
            kind=LIVE_SOURCE,
            path=path,
        )
    if path != DEFAULT_STATS_PATH:
        return MutationResultSource(
            stats=read_mutmut_stats(path),
            kind=LIVE_SOURCE,
            path=path,
        )
    artifact_source = latest_artifact_source()
    if artifact_source is not None:
        return artifact_source
    return MutationResultSource(
        stats=read_mutmut_stats(path),
        kind=LIVE_SOURCE,
        path=path,
    )


def latest_artifact_source() -> MutationResultSource | None:
    """Return newest parseable Mutmut run artifact stats available."""
    for stats_path in sorted(
        artifact_stats_paths(),
        key=artifact_sort_key,
        reverse=True,
    ):
        try:
            return MutationResultSource(
                stats=read_mutmut_stats(stats_path),
                kind=RUN_ARTIFACT_SOURCE,
                path=stats_path,
            )
        except (OSError, ValueError):
            continue
    for log_path in sorted(
        LOG_DIR.glob(f"*/{MUTMUT_LOG_NAME}"),
        key=artifact_sort_key,
        reverse=True,
    ):
        stats = stats_from_log(log_path)
        if stats is not None:
            return MutationResultSource(
                stats=stats,
                kind=RUN_ARTIFACT_SOURCE,
                path=log_path,
            )
    return None


def artifact_stats_paths() -> tuple[Path, ...]:
    """Return retained Mutmut stats artifacts outside live mutants/."""
    paths = tuple(LOG_DIR.glob(f"*/{MUTMUT_STATS_NAME}"))
    if SWEEP_LOG_DIR.exists():
        paths += tuple(SWEEP_LOG_DIR.glob(f"**/{MUTMUT_STATS_NAME}"))
    return paths


def artifact_sort_key(path: Path) -> tuple[int, str]:
    """Return deterministic newest-first artifact sort key."""
    try:
        mtime = path.stat().st_mtime_ns
    except OSError:
        mtime = 0
    return (mtime, path.as_posix())


def stats_from_log(path: Path) -> MutmutStats | None:
    """Parse Mutmut ratchet summary from a run log."""
    log_lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in reversed(log_lines):
        match = RATCHET_SUMMARY_RE.search(line)
        if match:
            return MutmutStats(
                killed=int(match.group("killed")),
                survived=int(match.group("survived")),
                total=int(match.group("total")),
                no_tests=0,
                skipped=0,
                suspicious=int(match.group("suspicious")),
                timeout=int(match.group("timeout")),
                check_was_interrupted_by_user=0,
                segfault=0,
            )
    return None


def render_json(stats: MutmutStats, source: MutationResultSource | None = None) -> str:
    """Render mutation result stats JSON."""
    payload: dict[str, object] = {
        "killed": stats.killed,
        "survived": stats.survived,
        "total": stats.total,
        "no_tests": stats.no_tests,
        "skipped": stats.skipped,
        "suspicious": stats.suspicious,
        "timeout": stats.timeout,
        "check_was_interrupted_by_user": stats.check_was_interrupted_by_user,
        "segfault": stats.segfault,
        "score": stats.score,
    }
    if source is not None:
        payload["source"] = {
            "kind": source.kind,
            "path": source.path.as_posix(),
        }
    return json.dumps(
        payload,
        indent=2,
        sort_keys=True,
    )


def render_text(stats: MutmutStats, source: MutationResultSource | None = None) -> str:
    """Render mutation result stats as compact text."""
    lines = [render_summary(stats)]
    if source is not None:
        source_path = source.path.as_posix()
        lines.append(f"Source: {source.kind} {source_path}")
    return "\n".join(lines)
