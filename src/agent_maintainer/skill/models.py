"""Typed models for packaged Agent Maintainer skills."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


@dataclass(frozen=True)
class SkillFile:
    """One packaged skill file with its stable content digest."""

    relative_path: str
    content: str
    digest: str


@dataclass(frozen=True)
class SkillBundle:
    """Portable setup skill files shipped by one package version."""

    name: str
    package_version: str
    files: tuple[SkillFile, ...]


class SkillState(StrEnum):
    """Ownership-aware installed skill state."""

    MISSING = "missing"
    CURRENT = "current"
    STALE = "stale"
    LOCALLY_MODIFIED = "locally-modified"


@dataclass(frozen=True)
class SkillManifest:
    """Managed skill ownership recorded inside one client directory."""

    schema_version: int
    skill: str
    client: str
    package_version: str
    files: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class SkillStatus:
    """Current state of one client skill installation."""

    client: str
    destination: Path
    state: SkillState
    package_version: str
    installed_version: str | None = None
    detail: str = ""
