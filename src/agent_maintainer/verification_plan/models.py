"""Immutable contracts for verification planning and path-risk policy."""

from __future__ import annotations

from dataclasses import dataclass

POLICY_SCHEMA_VERSION = 1
REPORT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class EvidenceRequirement:
    """One named changed-path evidence requirement."""

    id: str
    kind: str
    paths: tuple[str, ...]
    minimum: int = 1
    message: str = ""


@dataclass(frozen=True)
class PathRiskRule:
    """One ordered declarative path-risk rule."""

    id: str
    paths: tuple[str, ...]
    description: str = ""
    mode: str = "advisory"
    profiles: tuple[str, ...] = ()
    checks: tuple[str, ...] = ()
    review_categories: tuple[str, ...] = ()
    evidence: tuple[EvidenceRequirement, ...] = ()


@dataclass(frozen=True)
class PathRiskPolicy:
    """One validated path-risk policy document."""

    path: str
    rules: tuple[PathRiskRule, ...] = ()
    version: int = POLICY_SCHEMA_VERSION


@dataclass(frozen=True)
class PathClassification:
    """One ecosystem classification attached to an affected path."""

    path: str
    relation: str
    ecosystem: str
    role: str
    generated: bool = False
    ignored: bool = False


@dataclass(frozen=True)
class PlannedChange:
    """One structured Git change plus provider classifications."""

    path: str
    kind: str
    old_path: str | None = None
    classifications: tuple[PathClassification, ...] = ()


@dataclass(frozen=True)
class AffectedUnit:
    """One smallest-known repository unit affected by a diff."""

    kind: str
    name: str
    root: str
    changed_paths: tuple[str, ...]


@dataclass(frozen=True)
class RequirementResult:
    """Satisfied or missing evidence for one matched rule."""

    rule_id: str
    id: str
    mode: str
    kind: str
    paths: tuple[str, ...]
    minimum: int
    matched_paths: tuple[str, ...]
    status: str
    message: str


@dataclass(frozen=True)
class VerificationPlanReport:
    """Stable diff-aware verification plan report."""

    target: str
    base_ref: str
    staged: bool
    policy_path: str
    policy_configured: bool
    changes: tuple[PlannedChange, ...] = ()
    affected_units: tuple[AffectedUnit, ...] = ()
    matched_rules: tuple[str, ...] = ()
    selected_profiles: tuple[str, ...] = ()
    selected_checks: tuple[str, ...] = ()
    review_categories: tuple[str, ...] = ()
    requirements: tuple[RequirementResult, ...] = ()
    recommended_commands: tuple[str, ...] = ()
    advisories: tuple[str, ...] = ()
    blocking_findings: tuple[str, ...] = ()
    schema_version: int = REPORT_SCHEMA_VERSION
