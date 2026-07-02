"""Workspace configuration models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkspaceConfig:
    """One named workspace in a multi-package repository."""

    name: str
    source_roots: tuple[str, ...] = ()
    test_roots: tuple[str, ...] = ()
    package_paths: tuple[str, ...] = ()
    coverage_source: tuple[str, ...] = ()
