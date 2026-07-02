"""Internal ecosystem provider models."""

from __future__ import annotations

from dataclasses import dataclass

from agent_maintainer.config.schema import MaintainerConfig


@dataclass(frozen=True)
class EcosystemCheckContext:
    """Inputs needed by internal ecosystem providers to build checks."""

    config: MaintainerConfig
    compare_branch: str
    package_paths: tuple[str, ...]
