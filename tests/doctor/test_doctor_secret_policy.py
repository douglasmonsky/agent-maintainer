"""Tests focused secret-scanning doctor policy branches."""

from __future__ import annotations

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.doctor import cli as maintainer_doctor
from agent_maintainer.doctor.support import policy as maintainer_doctor_policy


def test_secret_scanning_policy_warns_when_history_scan_skips_security_profile() -> None:
    config = MaintainerConfig(
        enable_secret_scanning=True,
        secret_scan_history_profiles=("full",),
    )

    result = maintainer_doctor_policy.check_secret_scanning_policy(config)

    assert result.status == maintainer_doctor.WARNING
