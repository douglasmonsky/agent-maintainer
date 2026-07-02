"""Internal ecosystem provider models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from agent_maintainer.config.schema import MaintainerConfig


class ProviderMaturity(StrEnum):
    """Current support level for an ecosystem provider."""

    CORE = "core"
    EXPERIMENTAL = "experimental"


@dataclass(frozen=True)
class ProviderCommandSpec:
    """Configured-command field owned by one ecosystem provider."""

    check_name: str
    config_field: str


@dataclass(frozen=True)
class ProviderMetadata:
    """Internal metadata for a built-in ecosystem provider."""

    name: str
    display_name: str
    maturity: ProviderMaturity
    docs_path: str
    capabilities: tuple[str, ...]
    enabled_by_default: bool = False
    enabled_field: str | None = None
    command_specs: tuple[ProviderCommandSpec, ...] = field(default_factory=tuple)


class FileRole(StrEnum):
    """High-level repository file roles used by ecosystem classifiers."""

    SOURCE = "source"
    TEST = "test"
    GENERATED = "generated"
    CONFIG = "config"
    DOCS = "docs"
    DEPENDENCY = "dependency"
    IGNORED = "ignored"
    UNKNOWN = "unknown"


class ChangeKind(StrEnum):
    """Git-style change kinds used by advisory file-change classification."""

    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class FileClassification:
    """One ecosystem's classification for a repository path."""

    path: str
    ecosystem: str
    role: FileRole
    generated: bool = False
    ignored: bool = False
    reason: str = ""


@dataclass(frozen=True)
class FileChangeClassification:
    """One ecosystem's classification of a changed repository path."""

    path: str
    ecosystem: str
    role: FileRole
    change_kind: ChangeKind
    generated: bool = False
    ignored: bool = False
    reason: str = ""

    @classmethod
    def from_file_classification(
        cls,
        classification: FileClassification,
        *,
        change_kind: ChangeKind,
    ) -> FileChangeClassification:
        """Attach change metadata to a file classification."""
        return cls(
            path=classification.path,
            ecosystem=classification.ecosystem,
            role=classification.role,
            change_kind=change_kind,
            generated=classification.generated,
            ignored=classification.ignored,
            reason=classification.reason,
        )


@dataclass(frozen=True)
class SuppressionFinding:
    """One provider-owned suppression marker found in source text."""

    ecosystem: str
    kind: str
    line: str
    broad: bool
    reason: str


@dataclass(frozen=True)
class EcosystemCheckContext:
    """Inputs needed by internal ecosystem providers to build checks."""

    config: MaintainerConfig
    compare_branch: str
    package_paths: tuple[str, ...]
