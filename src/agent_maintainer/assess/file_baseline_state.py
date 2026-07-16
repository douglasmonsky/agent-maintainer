"""Versioned provider-neutral per-path file ceiling state and comparison."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, cast

BASELINE_VERSION = 1
MAX_BASELINE_BYTES = 2_000_000
MAX_BASELINE_ENTRIES = 20_000
COMMIT_PATTERN = re.compile(r"[0-9a-f]{7,64}")
WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")
ENTRY_FIELDS = frozenset(("group", "nonblank_ceiling", "path", "physical_ceiling"))


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
        if self.version != BASELINE_VERSION:
            raise ValueError(f"unsupported file ceiling baseline version: {self.version}")
        if COMMIT_PATTERN.fullmatch(self.source_commit) is None:
            raise ValueError("file ceiling baseline source_commit must be hexadecimal")
        keys = tuple(entry.key for entry in self.entries)
        if keys != tuple(sorted(keys)):
            raise ValueError("file ceiling baseline entries must be group/path sorted")
        if len(keys) != len(set(keys)):
            raise ValueError("file ceiling baseline contains duplicate group/path entries")


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


def render_baseline(baseline: FileCeilingBaseline) -> str:
    """Render canonical newline-terminated JSON."""
    payload = {
        "entries": [
            {
                "group": entry.group,
                "nonblank_ceiling": entry.nonblank_ceiling,
                "path": entry.path,
                "physical_ceiling": entry.physical_ceiling,
            }
            for entry in baseline.entries
        ],
        "source_commit": baseline.source_commit,
        "version": baseline.version,
    }
    return f"{json.dumps(payload, indent=2, sort_keys=True)}\n"


def parse_baseline(text: str) -> FileCeilingBaseline:
    """Parse one bounded strict file ceiling baseline document."""
    if len(text.encode("utf-8")) > MAX_BASELINE_BYTES:
        raise ValueError("file ceiling baseline exceeds the size limit")
    try:
        payload: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("file ceiling baseline is malformed JSON") from exc
    root = _object(payload, "file ceiling baseline")
    if set(root) != {"entries", "source_commit", "version"}:
        raise ValueError("file ceiling baseline has unexpected fields")
    version = _integer(root["version"], "version")
    source_commit = _string(root["source_commit"], "source_commit")
    raw_entries = root["entries"]
    if not isinstance(raw_entries, list):
        raise ValueError("file ceiling baseline entries must be an array")
    items = cast(list[Any], raw_entries)
    if len(items) > MAX_BASELINE_ENTRIES:
        raise ValueError("file ceiling baseline contains too many entries")
    entries = tuple(_parse_entry(item) for item in items)
    return FileCeilingBaseline(version, source_commit, entries)


def read_baseline(path: Path) -> FileCeilingBaseline:
    """Read one bounded file ceiling baseline."""
    if path.stat().st_size > MAX_BASELINE_BYTES:
        raise ValueError("file ceiling baseline exceeds the size limit")
    return parse_baseline(path.read_text(encoding="utf-8"))


def write_baseline(
    path: Path,
    baseline: FileCeilingBaseline,
    *,
    force: bool = False,
) -> None:
    """Write canonical JSON, refusing an unapproved overwrite."""
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if force else "x"
    try:
        with path.open(mode, encoding="utf-8", newline="\n") as handle:
            handle.write(render_baseline(baseline))
    except FileExistsError as exc:
        raise FileExistsError(f"baseline already exists: {path}") from exc


def _current_delta(
    observation: FileCeilingObservation,
    entry: FileCeilingEntry | None,
) -> FileCeilingDelta | None:
    physical_ceiling = observation.default_physical
    nonblank_ceiling = observation.default_nonblank
    if entry is not None:
        physical_ceiling = max(physical_ceiling, entry.physical_ceiling)
        nonblank_ceiling = max(nonblank_ceiling, entry.nonblank_ceiling)
    physical_regression = observation.default_physical > 0 and _exceeds(
        observation.physical,
        physical_ceiling,
    )
    nonblank_regression = observation.default_nonblank > 0 and _exceeds(
        observation.nonblank,
        nonblank_ceiling,
    )
    improved = entry is not None and (
        (observation.default_physical > 0 and observation.physical < entry.physical_ceiling)
        or (observation.default_nonblank > 0 and observation.nonblank < entry.nonblank_ceiling)
    )
    if not physical_regression and not nonblank_regression and not improved:
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


def _oversized(observation: FileCeilingObservation) -> bool:
    return _exceeds(observation.physical, observation.default_physical) or _exceeds(
        observation.nonblank,
        observation.default_nonblank,
    )


def _exceeds(value: int, ceiling: int) -> bool:
    return ceiling > 0 and value > ceiling


def _parse_entry(payload: Any) -> FileCeilingEntry:
    raw = _object(payload, "file ceiling entry")
    if frozenset(raw) != ENTRY_FIELDS:
        raise ValueError("file ceiling entry has unexpected fields")
    return FileCeilingEntry(
        _string(raw["group"], "entry.group"),
        _string(raw["path"], "entry.path"),
        _integer(raw["physical_ceiling"], "entry.physical_ceiling"),
        _integer(raw["nonblank_ceiling"], "entry.nonblank_ceiling"),
    )


def _object(payload: Any, label: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be an object")
    raw = cast(dict[object, Any], payload)
    if any(not isinstance(key, str) for key in raw):
        raise ValueError(f"{label} must use string keys")
    return cast(dict[str, Any], raw)


def _string(payload: Any, label: str) -> str:
    if not isinstance(payload, str):
        raise ValueError(f"{label} must be a string")
    return payload


def _integer(payload: Any, label: str) -> int:
    if not isinstance(payload, int) or isinstance(payload, bool):
        raise ValueError(f"{label} must be an integer")
    return payload


def _validate_group(value: str) -> None:
    if not value.strip():
        raise ValueError("file ceiling group must not be empty")


def _validate_path(value: str) -> None:
    normalized = value.strip().replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        not normalized
        or path.is_absolute()
        or ".." in path.parts
        or WINDOWS_DRIVE.match(normalized) is not None
        or path.as_posix() != normalized
    ):
        raise ValueError("file ceiling path must be normalized and repository-relative")


def _validate_counts(physical: int, nonblank: int, label: str) -> None:
    if (
        isinstance(physical, bool)
        or isinstance(nonblank, bool)
        or physical < 0
        or nonblank < 0
        or nonblank > physical
    ):
        raise ValueError(f"file ceiling {label} counts are invalid")


def _validate_limits(physical: int, nonblank: int) -> None:
    if isinstance(physical, bool) or isinstance(nonblank, bool) or physical < 0 or nonblank < 0:
        raise ValueError("file ceiling defaults must be non-negative integers")
