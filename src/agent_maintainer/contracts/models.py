"""Immutable domain models for semantic contract ratchets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ContractKind = Literal[
    "config-capabilities",
    "cli-manifest",
    "python-api",
    "json-schema",
]
Classification = Literal["breaking", "compatible", "review-required"]
BREAKING: Classification = "breaking"
COMPATIBLE: Classification = "compatible"
REVIEW_REQUIRED: Classification = "review-required"
VersionImpact = Literal["none", "prerelease", "patch", "minor", "major"]
ObligationStatus = Literal["satisfied", "unresolved"]
JsonObject = dict[str, object]


class ContractError(ValueError):
    """Base class for bounded contract-ratchet input failures."""


class PolicyError(ContractError):
    """Raised when authored contract policy is invalid."""


class BaselineError(ContractError):
    """Raised when generated contract baseline evidence is invalid."""


class ExtractionError(ContractError):
    """Raised when a configured contract cannot be safely extracted."""


class GitContractError(ContractError):
    """Raised when bounded historical contract state is unavailable or invalid."""


@dataclass(frozen=True)
class ContractSpec:
    """One authored semantic contract declaration."""

    id: str
    kind: ContractKind
    owner: str
    stability: str
    revision: int
    source: str
    exports: tuple[str, ...] = ()
    migration_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class ContractDecision:
    """One exact review decision for an otherwise ambiguous change."""

    contract: str
    fingerprint: str
    classification: Classification
    reason: str


@dataclass(frozen=True)
class ContractPolicy:
    """Strict repository-owned policy for configured contracts."""

    version: int = 1
    package_version_file: str = "pyproject.toml"
    pre_one_breaking: VersionImpact = "prerelease"
    stable_breaking: VersionImpact = "major"
    contracts: tuple[ContractSpec, ...] = ()
    decisions: tuple[ContractDecision, ...] = ()


@dataclass(frozen=True)
class Descriptor:
    """Normalized semantic facts for one configured contract."""

    contract_id: str
    kind: ContractKind
    owner: str
    stability: str
    revision: int
    sources: tuple[str, ...]
    body: JsonObject
    fingerprint: str


@dataclass(frozen=True)
class ContractBaseline:
    """Canonical generated descriptor snapshot."""

    schema_version: int = 1
    generator: str = "agent-maintainer"
    package_version: str = ""
    descriptors: tuple[Descriptor, ...] = ()


@dataclass(frozen=True)
class ContractChange:
    """One exact normalized semantic change."""

    contract_id: str
    operation: str
    path: str
    before: object | None
    after: object | None
    classification: Classification
    fingerprint: str
    reason: str

    def identity(self) -> tuple[str, str, str, str]:
        """Return the stable coordinates identifying this exact change."""

        return (self.contract_id, self.operation, self.path, self.fingerprint)


@dataclass(frozen=True)
class ContractObligation:
    """One independently evaluated revision, version, or migration obligation."""

    kind: str
    status: ObligationStatus
    message: str
    contract_id: str = ""
    minimum_impact: VersionImpact = "none"
    current: str = ""
    expected: str = ""
    fingerprints: tuple[str, ...] = ()
    missing_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class RepairFact:
    """One bounded machine-readable action for an unresolved finding."""

    contract_id: str
    fingerprint: str
    summary: str
    inspect_command: str
    kind: str = "contract-compatibility"


@dataclass(frozen=True)
class ContractReport:
    """Complete deterministic result of one contract-ratchet operation."""

    mode: str
    schema_version: int = 1
    base_ref: str = ""
    base_available: bool = False
    base_package_version: str = ""
    current_package_version: str = ""
    descriptors: tuple[Descriptor, ...] = ()
    changes: tuple[ContractChange, ...] = ()
    obligations: tuple[ContractObligation, ...] = ()
    decisions: tuple[ContractDecision, ...] = ()
    repair_facts: tuple[RepairFact, ...] = ()
    advisories: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    can_snapshot: bool = False

    @property
    def unresolved(self) -> bool:
        """Return whether invalid input or an exact obligation remains."""

        return bool(
            self.errors
            or any(item.status == "unresolved" for item in self.obligations)
            or any(item.classification == "review-required" for item in self.changes)
        )
