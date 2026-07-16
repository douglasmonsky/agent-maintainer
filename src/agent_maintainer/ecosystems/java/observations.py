"""Task-scoped Gradle outcomes and pre-run report evidence."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any

from agent_maintainer.config.java import JavaReportExpectation
from agent_maintainer.ecosystems.java.errors import JavaConfigurationError

MAX_GRADLE_OUTPUT_CHARS = 1_000_000
MAX_SNAPSHOT_BYTES = 20_971_520
DIGEST_CHUNK_BYTES = 65_536
TASK_LINE = re.compile(r"^> Task (?P<task>:\S+?)(?: (?P<state>[A-Z][A-Z-]*))?$")
SnapshotKey = tuple[str, tuple[str, ...], str]


class GradleTaskState(StrEnum):
    """Supported plain-console Gradle task outcomes."""

    SUCCESS = "success"
    FROM_CACHE = "from-cache"
    UP_TO_DATE = "up-to-date"
    NO_SOURCE = "no-source"
    SKIPPED = "skipped"
    FAILED = "failed"


_TASK_STATES = MappingProxyType(
    {
        "FROM-CACHE": GradleTaskState.FROM_CACHE,
        "UP-TO-DATE": GradleTaskState.UP_TO_DATE,
        "NO-SOURCE": GradleTaskState.NO_SOURCE,
        "SKIPPED": GradleTaskState.SKIPPED,
        "FAILED": GradleTaskState.FAILED,
    },
)


@dataclass(frozen=True)
class GradleTaskOutcome:
    """One requested task matched to one observed Gradle task line."""

    task: str
    gradle_task: str
    state: GradleTaskState


@dataclass(frozen=True)
class ReportSnapshot:
    """Digest evidence for one task-scoped report before Gradle runs."""

    tool: str
    tasks: tuple[str, ...]
    glob: str
    path: str
    sha256: str
    size: int


@dataclass(frozen=True)
class GradleObservation:
    """Requested task outcomes plus immutable pre-run report evidence."""

    requested_tasks: tuple[str, ...]
    task_outcomes: tuple[GradleTaskOutcome, ...]
    pre_run_reports: tuple[ReportSnapshot, ...]
    exit_code: int

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable artifact payload."""
        return asdict(self)


def build_gradle_observation(
    requested_tasks: tuple[str, ...],
    output: str,
    exit_code: int,
    pre_run_reports: tuple[ReportSnapshot, ...],
) -> GradleObservation:
    """Parse every requested task from bounded plain-console Gradle output."""
    if len(output) > MAX_GRADLE_OUTPUT_CHARS:
        raise JavaConfigurationError("Gradle output exceeds the observation limit")
    observed = _observed_task_lines(output)
    outcomes = tuple(_requested_outcome(task, observed) for task in requested_tasks)
    return GradleObservation(requested_tasks, outcomes, pre_run_reports, exit_code)


def snapshot_reports(
    gradle_root: Path,
    expectations: tuple[JavaReportExpectation, ...],
    requested_tasks: tuple[str, ...],
) -> tuple[ReportSnapshot, ...]:
    """Digest existing task-scoped reports without following paths outside the root."""
    canonical_root = gradle_root.resolve(strict=True)
    snapshots: dict[SnapshotKey, ReportSnapshot] = {}
    for expectation in expectations:
        if not _expectation_requested(expectation, requested_tasks):
            continue
        for pattern in expectation.globs:
            _validate_report_glob(pattern)
            for candidate in sorted(gradle_root.glob(pattern)):
                snapshot = _snapshot_candidate(canonical_root, candidate, expectation, pattern)
                key = (snapshot.tool, snapshot.tasks, snapshot.path)
                snapshots[key] = snapshot
    return tuple(snapshots[key] for key in sorted(snapshots))


def _observed_task_lines(output: str) -> tuple[tuple[str, GradleTaskState], ...]:
    observed: list[tuple[str, GradleTaskState]] = []
    for line in output.splitlines():
        match = TASK_LINE.fullmatch(line.strip())
        if match is None:
            continue
        task = match.group("task")
        state = _task_state(match.group("state"))
        observed.append((task, state))
    return tuple(observed)


def _task_state(value: str | None) -> GradleTaskState:
    if value is None:
        return GradleTaskState.SUCCESS
    try:
        return _TASK_STATES[value]
    except KeyError as exc:
        raise JavaConfigurationError(f"unsupported Gradle task outcome: {value}") from exc


def _requested_outcome(
    requested: str,
    observed: tuple[tuple[str, GradleTaskState], ...],
) -> GradleTaskOutcome:
    candidates = tuple(item for item in observed if _output_task_matches(requested, item[0]))
    if not candidates:
        raise JavaConfigurationError(f"missing requested Gradle task outcome: {requested}")
    if len(candidates) > 1:
        raise JavaConfigurationError(f"ambiguous requested Gradle task outcome: {requested}")
    gradle_task, state = next(iter(candidates))
    return GradleTaskOutcome(requested, gradle_task, state)


def _output_task_matches(requested: str, observed: str) -> bool:
    if requested.startswith(":"):
        return requested == observed
    return observed.rsplit(":", maxsplit=1)[-1] == requested


def _expectation_requested(
    expectation: JavaReportExpectation,
    requested_tasks: tuple[str, ...],
) -> bool:
    normalized_requested = {_normalize_configured_task(task) for task in requested_tasks}
    return any(
        _normalize_configured_task(task) in normalized_requested for task in expectation.tasks
    )


def _normalize_configured_task(task: str) -> str:
    return task if task.startswith(":") else f":{task}"


def _validate_report_glob(pattern: str) -> None:
    path = PurePosixPath(pattern)
    if path.is_absolute() or ".." in path.parts:
        raise JavaConfigurationError(f"unsafe Java report glob: {pattern}")


def _snapshot_candidate(
    canonical_root: Path,
    candidate: Path,
    expectation: JavaReportExpectation,
    pattern: str,
) -> ReportSnapshot:
    resolved = candidate.resolve(strict=True)
    try:
        relative = resolved.relative_to(canonical_root)
    except ValueError as exc:
        raise JavaConfigurationError(
            f"Java report match escapes Gradle root: {candidate.name}"
        ) from exc
    if not resolved.is_file():
        raise JavaConfigurationError(f"Java report match is not a file: {relative.as_posix()}")
    size = resolved.stat().st_size
    if size > MAX_SNAPSHOT_BYTES:
        raise JavaConfigurationError(f"Java report exceeds snapshot limit: {relative.as_posix()}")
    return ReportSnapshot(
        expectation.tool,
        expectation.tasks,
        pattern,
        relative.as_posix(),
        _file_digest(resolved),
        size,
    )


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        chunk = handle.read(DIGEST_CHUNK_BYTES)
        while chunk:
            digest.update(chunk)
            chunk = handle.read(DIGEST_CHUNK_BYTES)
    return digest.hexdigest()
