"""Independent contract-revision and package-version obligations."""

from __future__ import annotations

import tomllib
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import MappingProxyType
from typing import cast

from packaging.version import InvalidVersion, Version

from agent_maintainer.contracts.models import (
    ContractChange,
    ContractObligation,
    ContractPolicy,
    ContractSpec,
    VersionImpact,
)
from agent_maintainer.contracts.paths import read_confined_text

IMPACT_ORDER: Mapping[VersionImpact, int] = MappingProxyType(
    {
        "none": 0,
        "prerelease": 1,
        "patch": 2,
        "minor": 3,
        "major": 4,
    }
)
ADDITIVE_OPERATIONS = frozenset(("alias-change", "contract-add", "member-add"))


def contract_revision_obligations(
    base_policy: ContractPolicy,
    current_policy: ContractPolicy,
    changes: Sequence[ContractChange],
) -> tuple[ContractObligation, ...]:
    """Require exact revision stability or one-step breaking advancement."""

    base = {item.id: item for item in base_policy.contracts}
    current = {item.id: item for item in current_policy.contracts}
    by_contract = _changes_by_contract(changes)
    obligations = [
        _contract_revision_obligation(
            contract_id,
            base.get(contract_id),
            current.get(contract_id),
            by_contract.get(contract_id, ()),
        )
        for contract_id in sorted(set(base) | set(current) | set(by_contract))
    ]
    return tuple(obligations)


def package_version_obligation(
    base_version: str,
    current_version: str,
    policy: ContractPolicy,
    changes: Sequence[ContractChange],
) -> ContractObligation:
    """Return the minimum package-version obligation for semantic changes."""

    impact = _minimum_impact(policy, changes)
    fingerprints = tuple(sorted(item.fingerprint for item in changes))
    try:
        base, current = _version_pair(base_version, current_version)
    except InvalidVersion:
        return ContractObligation(
            kind="package-version",
            status="unresolved",
            message="package versions must be valid PEP 440 values",
            minimum_impact=impact,
            current=current_version,
            expected="valid PEP 440 version",
            fingerprints=fingerprints,
        )
    recommendation = recommended_version(base, impact)
    if recommendation is None:
        return ContractObligation(
            kind="package-version",
            status="unresolved",
            message="package version recommendation is ambiguous",
            minimum_impact=impact,
            current=current_version,
            expected="ambiguous",
            fingerprints=fingerprints,
        )
    satisfied = current >= recommendation
    return ContractObligation(
        kind="package-version",
        status="satisfied" if satisfied else "unresolved",
        message=(
            "package version satisfies the minimum recommendation"
            if satisfied
            else "package version is below the minimum recommendation"
        ),
        minimum_impact=impact,
        current=current_version,
        expected=str(recommendation),
        fingerprints=fingerprints,
    )


def _version_pair(base_version: str, current_version: str) -> tuple[Version, Version]:
    return Version(base_version), Version(current_version)


def recommended_version(base: Version, impact: VersionImpact) -> Version | None:
    """Return a concrete normalized recommendation when one is unambiguous."""

    if impact == "none":
        return base
    major, minor, patch = _release_triplet(base)
    epoch = f"{base.epoch}!" if base.epoch else ""
    if impact == "prerelease":
        return _recommended_prerelease(base, epoch, major, minor, patch)
    if impact == "patch":
        patch += 1
    elif impact == "minor":
        minor += 1
        patch = 0
    elif impact == "major":
        major += 1
        minor = 0
        patch = 0
    return Version(f"{epoch}{major}.{minor}.{patch}")


def _recommended_prerelease(
    base: Version,
    epoch: str,
    major: int,
    minor: int,
    patch: int,
) -> Version | None:
    if base.pre is None:
        return None
    label, number = base.pre
    next_number = number + 1
    return Version(f"{epoch}{major}.{minor}.{patch}{label}{next_number}")


def read_package_version(
    repo_root: Path,
    configured_path: str,
) -> str:
    """Read the exact static ``[project].version`` from confined TOML metadata."""

    text = read_confined_text(repo_root, configured_path, label="package version file")
    try:
        document = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError("package version file must be valid TOML") from exc
    project_value = document.get("project")
    _require(isinstance(project_value, dict), "package version file must contain a project table")
    project = cast(dict[str, object], project_value)
    raw_version = project.get("version")
    _require(isinstance(raw_version, str), "project version must be text")
    version = cast(str, raw_version)
    contains_control = any(ord(char) < ord(" ") for char in version)
    _require(
        bool(version) and version.strip() == version and not contains_control,
        "project version must be non-empty safe text",
    )
    return version


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _contract_revision_obligation(
    contract_id: str,
    base: ContractSpec | None,
    current: ContractSpec | None,
    changes: Sequence[ContractChange],
) -> ContractObligation:
    breaking = tuple(item for item in changes if item.classification == "breaking")
    expected = _expected_revision(base, has_breaking=bool(breaking))
    current_value = "missing" if current is None else str(current.revision)
    satisfied = current is not None and current.revision == expected
    return ContractObligation(
        kind="contract-revision",
        status="satisfied" if satisfied else "unresolved",
        message=(
            "contract revision satisfies semantic drift"
            if satisfied
            else "contract revision does not match semantic drift"
        ),
        contract_id=contract_id,
        current=current_value,
        expected=str(expected),
        fingerprints=tuple(sorted(item.fingerprint for item in breaking)),
    )


def _changes_by_contract(
    changes: Sequence[ContractChange],
) -> dict[str, tuple[ContractChange, ...]]:
    grouped: dict[str, list[ContractChange]] = {}
    for change in changes:
        grouped.setdefault(change.contract_id, []).append(change)
    return {
        contract_id: tuple(sorted(items, key=lambda item: item.identity()))
        for contract_id, items in grouped.items()
    }


def _expected_revision(base: ContractSpec | None, *, has_breaking: bool) -> int:
    if base is None:
        return 1
    return base.revision + 1 if has_breaking else base.revision


def _minimum_impact(
    policy: ContractPolicy,
    changes: Sequence[ContractChange],
) -> VersionImpact:
    specs = {item.id: item for item in policy.contracts}
    impact: VersionImpact = "none"
    for change in changes:
        candidate = _change_impact(change, specs.get(change.contract_id), policy)
        if IMPACT_ORDER[candidate] > IMPACT_ORDER[impact]:
            impact = candidate
    return impact


def _change_impact(
    change: ContractChange,
    spec: ContractSpec | None,
    policy: ContractPolicy,
) -> VersionImpact:
    if change.classification == "review-required":
        return "none"
    stability = "stable" if spec is None else spec.stability
    if change.classification == "breaking":
        return policy.pre_one_breaking if stability == "beta" else policy.stable_breaking
    if stability == "beta":
        return "prerelease"
    return "minor" if change.operation in ADDITIVE_OPERATIONS else "patch"


def _release_triplet(version: Version) -> tuple[int, int, int]:
    release = (*version.release, 0, 0, 0)
    return release[0], release[1], release[2]
