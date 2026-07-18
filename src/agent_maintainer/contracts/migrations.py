"""Migration-evidence obligations for exact breaking contract changes."""

from __future__ import annotations

import fnmatch
from collections.abc import Sequence
from typing import Protocol

from agent_maintainer.contracts.models import (
    ContractChange,
    ContractObligation,
    ContractPolicy,
)
from agent_maintainer.core.repo_paths import RepoPathError, validate_repo_path

EVIDENCE_KINDS = frozenset(("added", "modified", "renamed"))


class GitPathFact(Protocol):
    """Structural Git path fact accepted by migration evaluation."""

    @property
    def path(self) -> str:
        """Return the current or destination repository path."""

        raise NotImplementedError

    @property
    def kind(self) -> str:
        """Return the normalized Git change kind."""

        raise NotImplementedError


def migration_obligations(
    policy: ContractPolicy,
    changes: Sequence[ContractChange],
    git_changes: Sequence[GitPathFact],
) -> tuple[ContractObligation, ...]:
    """Require changed contract-local migration evidence for every break."""

    specs = {item.id: item for item in policy.contracts}
    breaking: dict[str, list[ContractChange]] = {}
    for change in changes:
        if change.classification == "breaking":
            breaking.setdefault(change.contract_id, []).append(change)
    evidence_paths = tuple(
        sorted({item.path for item in git_changes if item.kind in EVIDENCE_KINDS})
    )
    obligations = [
        _migration_obligation(
            contract_id,
            specs[contract_id].migration_paths if contract_id in specs else (),
            contract_changes,
            evidence_paths,
        )
        for contract_id, contract_changes in sorted(breaking.items())
    ]
    return tuple(obligations)


def _migration_obligation(
    contract_id: str,
    configured_paths: tuple[str, ...],
    changes: Sequence[ContractChange],
    evidence_paths: Sequence[str],
) -> ContractObligation:
    satisfied = any(
        _path_matches(pattern, path) for pattern in configured_paths for path in evidence_paths
    )
    return ContractObligation(
        kind="migration-evidence",
        status="satisfied" if satisfied else "unresolved",
        message=(
            "changed migration evidence satisfies breaking contract"
            if satisfied
            else "breaking contract requires changed migration evidence"
        ),
        contract_id=contract_id,
        fingerprints=tuple(sorted(item.fingerprint for item in changes)),
        missing_paths=() if satisfied else tuple(sorted(configured_paths)),
    )


def _path_matches(pattern: str, path: str) -> bool:
    pattern_parts = _validated_segments(pattern, label="migration pattern")
    path_parts = _validated_segments(path, label="migration evidence path")
    reachable: set[int] = {0}
    for pattern_part in pattern_parts:
        if pattern_part == "**":
            reachable = set(range(min(reachable), len(path_parts) + 1)) if reachable else set()
            continue
        reachable = {
            index + 1
            for index in reachable
            if index < len(path_parts) and fnmatch.fnmatchcase(path_parts[index], pattern_part)
        }
    return len(path_parts) in reachable


def _validated_segments(value: str, *, label: str) -> tuple[str, ...]:
    try:
        validated = validate_repo_path(value, label=label)
    except RepoPathError as exc:
        raise ValueError(str(exc)) from exc
    if any("**" in segment and segment != "**" for segment in validated.split("/")):
        raise ValueError(f"{label} must use ** only as a complete segment")
    return tuple(validated.split("/"))
