"""Tests focused secret-scanning doctor policy branches."""

from __future__ import annotations

from guardrail_lib.config.schema import GuardrailConfig
from scripts import guardrail_doctor, guardrail_doctor_policy


def test_secret_scanning_policy_warns_when_history_scan_skips_security_profile() -> None:
    config = GuardrailConfig(
        enable_secret_scanning=True,
        secret_scan_history_profiles=("full",),
    )

    result = guardrail_doctor_policy.check_secret_scanning_policy(config)

    assert result.status == guardrail_doctor.WARNING
