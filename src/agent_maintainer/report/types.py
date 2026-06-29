"""Typed report rendering value objects."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReportPaths:
    """Filesystem locations used while rendering a static report."""

    log_dir: Path
    output_dir: Path


@dataclass(frozen=True)
class NamedCheckSection:
    """Report section metadata for a named set of checks."""

    section_id: str
    title: str
    names: frozenset[str]
