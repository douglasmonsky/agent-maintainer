"""Shared models for architecture policy governance."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ArchitecturePolicyChange:
    """Changed architecture policy paths requiring a decision note."""

    paths: tuple[str, ...]

    def format_paths(self) -> str:
        """Return a compact display string for changed policy paths."""
        return ", ".join(self.paths)
