"""Internal ecosystem provider models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.models import Check


@dataclass(frozen=True)
class EcosystemCheckContext:
    """Inputs needed by internal ecosystem providers to build checks."""

    config: MaintainerConfig
    base_ref: str
    compare_branch: str
    staged: bool
    package_paths: tuple[str, ...]


class EcosystemProvider(Protocol):
    """Private provider seam for ecosystem-owned check generation."""

    name: str

    def checks(self, context: EcosystemCheckContext) -> list[Check]:
        """Build checks owned by this ecosystem."""
        ...
