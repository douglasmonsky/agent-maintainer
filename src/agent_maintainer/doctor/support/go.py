"""Doctor checks for experimental Go provider setup."""

from __future__ import annotations

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.doctor.support.models import DoctorResult
from agent_maintainer.doctor.support.providers import check_go_provider


def check_provider(config: MaintainerConfig) -> tuple[DoctorResult, ...]:
    """Return Go provider setup health rows."""
    return check_go_provider(config)
