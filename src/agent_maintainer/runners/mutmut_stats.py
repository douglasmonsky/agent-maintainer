"""Parse and ratchet Mutmut result statistics."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from agent_maintainer.core.structured_values import json_object

DEFAULT_STATS_PATH = Path("mutants/mutmut-cicd-stats.json")


@dataclass(frozen=True)
class MutmutStats:
    """Machine-readable Mutmut result counters."""

    killed: int
    survived: int
    total: int
    no_tests: int
    skipped: int
    suspicious: int
    timeout: int
    check_was_interrupted_by_user: int
    segfault: int

    @property
    def score(self) -> float:
        """Return killed-mutant percentage."""

        if self.total <= 0:
            return 100.0
        return (self.killed / self.total) * 100


@dataclass(frozen=True)
class MutmutRatchet:
    """Mutation result ratchet thresholds."""

    enabled: bool = False
    max_survivors: int = 0
    max_suspicious: int = 0
    max_timeouts: int = 0
    min_score: int = 0


def read_stats(path: Path = DEFAULT_STATS_PATH) -> MutmutStats:
    """Read Mutmut CI/CD stats from JSON output."""

    with path.open(encoding="utf-8") as handle:
        payload: object = json.load(handle)
    stats = json_object(payload)
    if stats is None:
        raise ValueError("mutmut stats must be a JSON object")
    return stats_from_mapping(stats)


def stats_from_mapping(payload: dict[str, object]) -> MutmutStats:
    """Convert raw Mutmut stats mapping to typed counters."""

    return MutmutStats(
        killed=as_int(payload, "killed"),
        survived=as_int(payload, "survived"),
        total=as_int(payload, "total"),
        no_tests=as_int(payload, "no_tests"),
        skipped=as_int(payload, "skipped"),
        suspicious=as_int(payload, "suspicious"),
        timeout=as_int(payload, "timeout"),
        check_was_interrupted_by_user=as_int(payload, "check_was_interrupted_by_user"),
        segfault=as_int(payload, "segfault"),
    )


def as_int(payload: dict[str, object], key: str) -> int:
    """Return nonnegative integer counter from Mutmut payload."""

    value = payload.get(key, 0)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"mutmut stats field {key!r} must be a nonnegative integer")
    return value


def ratchet_issues(stats: MutmutStats, ratchet: MutmutRatchet) -> tuple[str, ...]:
    """Return mutation result ratchet failures."""

    if not ratchet.enabled:
        return ()
    issues: list[str] = []
    if stats.survived > ratchet.max_survivors:
        issues.append(
            f"mutmut survived mutants {stats.survived} above allowed {ratchet.max_survivors}"
        )
    if stats.suspicious > ratchet.max_suspicious:
        issues.append(
            f"mutmut suspicious mutants {stats.suspicious} above allowed {ratchet.max_suspicious}"
        )
    if stats.timeout > ratchet.max_timeouts:
        issues.append(
            f"mutmut timeout mutants {stats.timeout} above allowed {ratchet.max_timeouts}"
        )
    if ratchet.min_score > 0 and stats.score < ratchet.min_score:
        issues.append(f"mutmut score {stats.score:.2f}% below required {ratchet.min_score}%")
    return tuple(issues)


def render_summary(stats: MutmutStats) -> str:
    """Return compact mutation result summary."""

    return (
        f"mutmut score {stats.score:.2f}% "
        f"({stats.killed}/{stats.total} killed, {stats.survived} survived, "
        f"{stats.suspicious} suspicious, {stats.timeout} timeout)"
    )
