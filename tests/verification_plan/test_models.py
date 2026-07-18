"""Immutable verification-plan model tests."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from agent_maintainer.verification_plan.models import (
    POLICY_SCHEMA_VERSION,
    REPORT_SCHEMA_VERSION,
    AffectedUnit,
    EvidenceRequirement,
    PathRiskPolicy,
    PathRiskRule,
    VerificationPlanReport,
)


def test_policy_models_default_to_advisory_tuple_contracts() -> None:
    requirement = EvidenceRequirement(
        id="architecture-decision",
        kind="changed-path",
        paths=("docs/architecture/decisions/*.md",),
    )
    rule = PathRiskRule(
        id="architecture-policy",
        paths=("tach.toml",),
        evidence=(requirement,),
    )
    policy = PathRiskPolicy(path=".agent-maintainer/path-risk.toml", rules=(rule,))

    assert policy.version == POLICY_SCHEMA_VERSION == 1
    assert rule.mode == "advisory"
    assert rule.profiles == ()
    assert requirement.minimum == 1


def test_report_has_stable_empty_contract() -> None:
    report = VerificationPlanReport(
        target="/repo",
        base_ref="origin/main",
        staged=False,
        policy_path=".agent-maintainer/path-risk.toml",
        policy_configured=False,
    )

    assert report.schema_version == REPORT_SCHEMA_VERSION == 1
    assert report.changes == ()
    assert report.affected_units == ()
    assert report.blocking_findings == ()


def test_models_are_frozen() -> None:
    unit = AffectedUnit(
        kind="repository",
        name="repository",
        root=".",
        changed_paths=("README.md",),
    )

    with pytest.raises(FrozenInstanceError):
        unit.name = "changed"  # type: ignore[misc]
