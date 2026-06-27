"""Compatibility facade for Archguard Tach validation."""

from __future__ import annotations

from pathlib import Path

from archguard.tach_config import tach_config_issues as archguard_tach_config_issues


def tach_config_issues(repo_root: Path, *, require_strict_root: bool) -> list[str]:
    """Return Tach configuration problems from Archguard."""
    return archguard_tach_config_issues(
        repo_root,
        require_strict_root=require_strict_root,
    )
