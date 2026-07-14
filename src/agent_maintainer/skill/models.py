"""Typed models for packaged Agent Maintainer skills."""

from __future__ import annotations

from dataclasses import dataclass


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
