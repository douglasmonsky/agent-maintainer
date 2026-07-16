"""Versioned provider-neutral per-path file ceiling state and comparison."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath

BASELINE_VERSION = 1
MAX_BASELINE_ENTRIES = 20_000
WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")
COMMIT_PATTERN = re.compile(r"[0-9a-f]{7,64}")


@dataclass(frozen=True)
class FileCeilingObservation:
    """Current counts and configured new-file defaults for one group/path pair."""

    group: str
    path: str
    physical: int
    nonblank: int
    default_physical: int
    default_nonblank: int

    def __post_init__(self) -> None:
        """Validate one normalized provider-neutral observation."""
        _validate_group(self.group)
        _validate_path(self.path)
        _validate_counts(self.physical, self.nonblank, "observation")
        _validate_limits(self.default_physical, self.default_nonblank)

    @property
    def key(self) -> tuple[str, str]:
        """Return the stable group/path identity."""
        return self.group, self.path


@dataclass(frozen=True)
class FileCeilingEntry:
    """Established physical/nonblank ceilings for one provider-neutral path."""

    group: str
    path: str
    physical_ceiling: int
    nonblank_ceiling: int

    def __post_init__(self) -> None:
        """Validate deterministic entry invariants."""
        _validate_group(self.group)
        _validate_path(self.path)
        _validate_limits(self.physical_ceiling, self.nonblank_ceiling)

    @property
    def key(self) -> tuple[str, str]:
        """Return the stable group/path identity."""
        return self.group, self.path


@dataclass(frozen=True)
class FileCeilingBaseline:
    """Versioned deterministic per-path ceiling document."""

    version: int
    source_commit: str
    entries: tuple[FileCeilingEntry, ...]

    def __post_init__(self) -> None:
        """Reject unsupported, duplicate, or noncanonical documents."""
        self._validate_header()
        keys = tuple(entry.key for entry in self.entries)
        if keys != tuple(sorted(keys)):
            raise ValueError("file ceiling baseline entries must be group/path sorted")
        if len(keys) != len(set(keys)):
            raise ValueError("file ceiling baseline contains duplicate group/path entries")

    def _validate_header(self) -> None:
        if self.version != BASELINE_VERSION:
            raise ValueError(f"unsupported file ceiling baseline version: {self.version}")
        if COMMIT_PATTERN.fullmatch(self.source_commit) is None:
            raise ValueError("file ceiling baseline source_commit must be hexadecimal")


@dataclass(frozen=True)
class FileCeilingDelta:
    """One regression or explicit-prune opportunity."""

    group: str
    path: str
    physical: int
    nonblank: int
    physical_ceiling: int
    nonblank_ceiling: int
    physical_regression: bool = False
    nonblank_regression: bool = False
    improved: bool = False
    removed: bool = False
    new_path: bool = False

    @property
    def regressed(self) -> bool:
        """Return whether either active dimension exceeded its ceiling."""
        return self.physical_regression or self.nonblank_regression


@dataclass(frozen=True)
class FileCeilingComparison:
    """Deterministic comparison deltas for current repository files."""

    deltas: tuple[FileCeilingDelta, ...]

    @property
    def passed(self) -> bool:
        """Return whether current files add no new or larger debt."""
        return not any(delta.regressed for delta in self.deltas)


@dataclass(frozen=True)
class FileCeilingBaselineSummary:
    """Bounded inspect output for one per-path ceiling baseline."""

    version: int
    source_commit: str
    entry_count: int
    group_count: int


def create_baseline(
    observations: tuple[FileCeilingObservation, ...],
    *,
    source_commit: str,
) -> FileCeilingBaseline:
    """Record only files currently exceeding their configured new-file defaults."""
    entries = tuple(
        FileCeilingEntry(
            item.group,
            item.path,
            item.physical if item.default_physical > 0 else 0,
            item.nonblank if item.default_nonblank > 0 else 0,
        )
        for item in sorted(observations, key=lambda value: value.key)
        if _oversized(item)
    )
    if len(entries) > MAX_BASELINE_ENTRIES:
        raise ValueError("file ceiling baseline contains too many entries")
    return FileCeilingBaseline(BASELINE_VERSION, source_commit.lower(), entries)


def compare_baseline(
    stored: FileCeilingBaseline | None,
    observations: tuple[FileCeilingObservation, ...],
) -> FileCeilingComparison:
    """Compare current files to new-file defaults and established ceilings."""
    entries = {} if stored is None else {entry.key: entry for entry in stored.entries}
    current = {item.key: item for item in observations}
    deltas: list[FileCeilingDelta] = []
    for key in sorted(current):
        observation = current[key]
        entry = entries.get(key)
        delta = _current_delta(observation, entry)
        if delta is not None:
            deltas.append(delta)
    for key in sorted(set(entries) - set(current)):
        entry = entries[key]
        deltas.append(
            FileCeilingDelta(
                entry.group,
                entry.path,
                0,
                0,
                entry.physical_ceiling,
                entry.nonblank_ceiling,
                improved=True,
                removed=True,
            )
        )
    return FileCeilingComparison(tuple(deltas))


def prune_baseline(
    stored: FileCeilingBaseline,
    observations: tuple[FileCeilingObservation, ...],
    *,
    source_commit: str,
) -> FileCeilingBaseline:
    """Remove resolved paths and lower improved ceilings without admitting debt."""
    comparison = compare_baseline(stored, observations)
    if not comparison.passed:
        raise ValueError("file ceiling prune contains new or regressed paths")
    return create_baseline(observations, source_commit=source_commit)


def inspect_baseline(baseline: FileCeilingBaseline) -> FileCeilingBaselineSummary:
    """Return a concise deterministic baseline summary."""
    return FileCeilingBaselineSummary(
        baseline.version,
        baseline.source_commit,
        len(baseline.entries),
        len({entry.group for entry in baseline.entries}),
    )


def _current_delta(
    observation: FileCeilingObservation,
    entry: FileCeilingEntry | None,
) -> FileCeilingDelta | None:
    physical_ceiling, nonblank_ceiling = _active_ceilings(observation, entry)
    physical_regression, nonblank_regression = _regression_flags(
        observation,
        physical_ceiling,
        nonblank_ceiling,
    )
    improved = _is_improved(observation, entry)
    if not any((physical_regression, nonblank_regression, improved)):
        return None
    return FileCeilingDelta(
        observation.group,
        observation.path,
        observation.physical,
        observation.nonblank,
        physical_ceiling,
        nonblank_ceiling,
        physical_regression,
        nonblank_regression,
        improved and not (physical_regression or nonblank_regression),
        new_path=entry is None,
    )


def _active_ceilings(
    observation: FileCeilingObservation,
    entry: FileCeilingEntry | None,
) -> tuple[int, int]:
    if entry is None:
        return observation.default_physical, observation.default_nonblank
    return (
        max(observation.default_physical, entry.physical_ceiling),
        max(observation.default_nonblank, entry.nonblank_ceiling),
    )


def _regression_flags(
    observation: FileCeilingObservation,
    physical_ceiling: int,
    nonblank_ceiling: int,
) -> tuple[bool, bool]:
    return (
        observation.default_physical > 0 and observation.physical > physical_ceiling,
        observation.default_nonblank > 0 and observation.nonblank > nonblank_ceiling,
    )


def _is_improved(
    observation: FileCeilingObservation,
    entry: FileCeilingEntry | None,
) -> bool:
    if entry is None:
        return False
    physical = observation.default_physical > 0 and observation.physical < entry.physical_ceiling
    nonblank = observation.default_nonblank > 0 and observation.nonblank < entry.nonblank_ceiling
    return physical or nonblank


def _oversized(observation: FileCeilingObservation) -> bool:
    return _exceeds(observation.physical, observation.default_physical) or _exceeds(
        observation.nonblank,
        observation.default_nonblank,
    )


def _exceeds(value: int, ceiling: int) -> bool:
    if ceiling <= 0:
        return False
    return value > ceiling


def _validate_group(value: str) -> None:
    if not value.strip():
        raise ValueError("file ceiling group must not be empty")


def _validate_path(value: str) -> None:
    normalized = value.strip().replace("\\", "/")
    path = PurePosixPath(normalized)
    invalid = (
        not normalized,
        path.is_absolute(),
        ".." in path.parts,
        WINDOWS_DRIVE.match(normalized) is not None,
        path.as_posix() != normalized,
    )
    if any(invalid):
        raise ValueError("file ceiling path must be normalized and repository-relative")


def _validate_counts(physical: int, nonblank: int, label: str) -> None:
    invalid = (
        isinstance(physical, bool),
        isinstance(nonblank, bool),
        physical < 0,
        nonblank < 0,
        nonblank > physical,
    )
    if any(invalid):
        raise ValueError(f"file ceiling {label} counts are invalid")


def _validate_limits(physical: int, nonblank: int) -> None:
    if isinstance(physical, bool) or isinstance(nonblank, bool) or physical < 0 or nonblank < 0:
        raise ValueError("file ceiling defaults must be non-negative integers")
