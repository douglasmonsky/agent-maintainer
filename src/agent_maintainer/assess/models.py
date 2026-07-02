"""Typed assessment report models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, cast


@dataclass(frozen=True)
class RepoEvidence:
    """Repository facts used by advisory assessments."""

    target: str
    has_agent_config: bool
    has_pyproject: bool
    has_git: bool
    has_tests: bool
    has_src: bool
    has_ci: bool
    has_pre_commit: bool
    has_agent_guidance: bool
    has_codex_hooks: bool
    has_claude_hooks: bool
    has_tach: bool
    has_import_linter: bool
    has_lock_file: bool
    has_dependency_file: bool
    has_package_json: bool
    has_go_mod: bool
    has_container_or_iac: bool
    python_files: int
    source_files: int
    test_files: int
    yaml_files: int
    toml_files: int
    json_files: int
    scanned_files: int = 0
    scan_source: str = "unknown"
    scan_truncated: bool = False


@dataclass(frozen=True)
class GateRecommendation:
    """One optional gate recommendation."""

    name: str
    recommendation: str
    reason: str
    config_key: str
    profiles: tuple[str, ...]


@dataclass(frozen=True)
class SetupAdvisorReport:
    """Recommended Agent Maintainer setup for a repository."""

    target: str
    track: str
    preset: str
    confidence: str
    reasons: tuple[str, ...]
    optional_gates: tuple[GateRecommendation, ...]
    agent_prompts: tuple[str, ...]
    next_commands: tuple[str, ...]
    evidence: RepoEvidence


@dataclass(frozen=True)
class DebtCategory:
    """One Technical Debt Score category."""

    name: str
    score: int
    weight: int
    status: str
    evidence: tuple[str, ...]
    recommendations: tuple[str, ...]


@dataclass(frozen=True)
class DebtScoreReport:
    """Transparent advisory technical debt score."""

    target: str
    score: int
    risk: str
    confidence: str
    summary: str
    categories: tuple[DebtCategory, ...]
    next_actions: tuple[str, ...]
    artifact_paths: tuple[str, ...]
    evidence: RepoEvidence


@dataclass(frozen=True)
class ReviewabilityChange:
    """One advisory changed-file classification."""

    path: str
    ecosystem: str
    role: str
    change_kind: str
    added: int
    deleted: int
    generated: bool = False
    ignored: bool = False


@dataclass(frozen=True)
class ReviewabilityCount:
    """Count for one advisory reviewability grouping."""

    key: str
    count: int


@dataclass(frozen=True)
class ReviewabilityReport:
    """Advisory provider-aware reviewability summary."""

    target: str
    base_ref: str
    staged: bool
    total_changed_files: int
    classified_files: int
    unclassified_files: int
    by_ecosystem: tuple[ReviewabilityCount, ...]
    by_role: tuple[ReviewabilityCount, ...]
    changes: tuple[ReviewabilityChange, ...]
    advisory_note: str
    next_commands: tuple[str, ...]


def to_dict(value: object) -> object:
    """Return a JSON-serializable dataclass value."""
    if hasattr(value, "__dataclass_fields__"):
        return asdict(cast(Any, value))
    return value
