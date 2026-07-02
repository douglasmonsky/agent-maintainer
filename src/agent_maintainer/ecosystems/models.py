"""Internal ecosystem provider models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from agent_maintainer.config.schema import MaintainerConfig


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
class EcosystemCheckContext:
    """Inputs needed by internal ecosystem providers to build checks."""

    config: MaintainerConfig
    compare_branch: str
    package_paths: tuple[str, ...]
