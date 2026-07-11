"""Rank ratchet findings into repair targets."""

from __future__ import annotations

import subprocess  # nosec B404
from dataclasses import dataclass

from agent_maintainer.ratchet.models import RatchetStatusEntry, RatchetStatusReport

STATUS_WEIGHTS = (
    ("new", 100),
    ("worsened", 80),
    ("unchanged", 30),
    ("improved", 10),
    ("resolved", 0),
)
CHANGED_PATH_BONUS = 25


@dataclass(frozen=True)
class RatchetTarget:
    """One ranked ratchet repair target."""

    rank: int
    path: str
    check: str
    status: str
    score: int
    why: str
    current: str
    first_command: str

    def to_dict(self) -> dict[str, int | str]:
        """Return stable JSON object."""

        return {
            "rank": self.rank,
            "path": self.path,
            "check": self.check,
            "status": self.status,
            "score": self.score,
            "why": self.why,
            "current": self.current,
            "first_command": self.first_command,
        }


def ranked_targets(
    report: RatchetStatusReport,
    *,
    changed_path_set: set[str],
    limit: int,
) -> tuple[RatchetTarget, ...]:
    """Return top ranked ratchet targets."""

    candidates = [
        target_candidate(entry, changed_path_set)
        for entry in report.entries
        if entry.status != "resolved"
    ]
    ordered = sorted(candidates, key=target_sort_key)
    return tuple(
        target_with_rank(target, rank) for rank, target in enumerate(ordered[:limit], start=1)
    )


def target_candidate(
    entry: RatchetStatusEntry,
    changed_path_set: set[str],
) -> RatchetTarget:
    """Return an unranked target for one status entry."""

    finding = entry.finding
    path_changed = finding.path in changed_path_set
    score = status_weight(entry.status)
    if path_changed:
        score += CHANGED_PATH_BONUS
    return RatchetTarget(
        rank=0,
        path=finding.path,
        check=finding.check,
        status=entry.status,
        score=score,
        why=why_target(entry, path_changed),
        current=current_summary(entry),
        first_command=first_context_command(finding.path),
    )


def why_target(entry: RatchetStatusEntry, path_changed: bool) -> str:
    """Return compact human reason for target priority."""

    status = entry.status
    check = entry.finding.check
    parts = [f"{status} {check} violation"]
    if path_changed:
        parts.append("in current diff")
    return " ".join(parts)


def current_summary(entry: RatchetStatusEntry) -> str:
    """Return compact metric summary for a target."""

    finding = entry.finding
    if finding.metric is None:
        return finding.message
    return f"{finding.metric}: {finding.value} (threshold: {finding.threshold})"


def first_context_command(path: str) -> str:
    """Return first safe expansion command for a target path."""

    return f"python -m agent_maintainer context file {path} --outline"


def target_sort_key(target: RatchetTarget) -> tuple[int, str, str]:
    """Return deterministic descending-priority sort key."""

    return (-target.score, target.path, target.check)


def target_with_rank(target: RatchetTarget, rank: int) -> RatchetTarget:
    """Return target with final one-based rank."""

    return RatchetTarget(
        rank=rank,
        path=target.path,
        check=target.check,
        status=target.status,
        score=target.score,
        why=target.why,
        current=target.current,
        first_command=target.first_command,
    )


def status_weight(status: str) -> int:
    """Return ranking weight for a status."""

    for candidate, weight in STATUS_WEIGHTS:
        if candidate == status:
            return weight
    return 0


def changed_paths(base_ref: str) -> set[str]:
    """Return paths changed relative to a base ref."""

    if (
        not base_ref
        or base_ref.strip() != base_ref
        or base_ref.startswith("-")
        or any(character.isspace() or not character.isprintable() for character in base_ref)
    ):
        return set()
    try:
        result = subprocess.run(  # nosec B603
            ("git", "diff", "--name-only", base_ref, "--"),
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return set()
    return {line for line in result.stdout.splitlines() if line}
