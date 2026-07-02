"""Doctor checks for experimental TypeScript provider setup."""

from __future__ import annotations

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.doctor.support.models import DoctorResult
from agent_maintainer.doctor.support.providers import check_typescript_provider


def check_provider(config: MaintainerConfig) -> tuple[DoctorResult, ...]:
    """Return TypeScript provider setup health rows."""
    return check_typescript_provider(config)
