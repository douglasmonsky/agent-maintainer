"""Deterministic verification-plan rendering tests."""

from __future__ import annotations

import json

from agent_maintainer.verification_plan.models import (
    AffectedUnit,
    PathClassification,
    PlannedChange,
    RequirementResult,
    VerificationPlanReport,
)
from agent_maintainer.verification_plan.reporting import render_json, render_text


def test_json_contract_is_explicit_and_byte_stable() -> None:
    report = _report()

    first = render_json(report)
    second = render_json(report)
    payload = json.loads(first)

    assert first == second
    assert first.endswith("\n")
    assert tuple(payload) == tuple(sorted(payload))
    assert payload["schema_version"] == 1
    assert payload["changes"][0] == {
        "classifications": [
            {
                "ecosystem": "python",
                "generated": False,
                "ignored": False,
                "path": "src/new.py",
                "relation": "destination",
                "role": "source",
            },
        ],
        "kind": "renamed",
        "old_path": "src/old.py",
        "path": "src/new.py",
    }
    assert payload["requirements"][0]["status"] == "missing"
    assert "timestamp" not in first


def test_text_contains_bounded_contract_sections_and_final_blocker() -> None:
    rendered = render_text(_report())

    for heading in (
        "Policy",
        "Changed paths",
        "Affected units",
        "Requirements",
        "Review categories",
        "Recommended commands",
        "Advisories",
        "Blocking findings",
    ):
        assert f"{heading}:" in rendered
    assert rendered.endswith("architecture/adr: Add an ADR.\n")


def test_text_ends_ready_when_no_blockers() -> None:
    report = VerificationPlanReport(
        target="/repo",
        base_ref="main",
        staged=False,
        policy_path="policy.toml",
        policy_configured=True,
    )

    assert render_text(report).endswith("Ready:\n- No blocking findings.\n")


def _report() -> VerificationPlanReport:
    return VerificationPlanReport(
        target="/repo",
        base_ref="main",
        staged=False,
        policy_path="policy.toml",
        policy_configured=True,
        changes=(
            PlannedChange(
                path="src/new.py",
                kind="renamed",
                old_path="src/old.py",
                classifications=(
                    PathClassification(
                        path="src/new.py",
                        relation="destination",
                        ecosystem="python",
                        role="source",
                    ),
                ),
            ),
        ),
        affected_units=(
            AffectedUnit("python-package", "app", "src", ("src/new.py",)),
        ),
        matched_rules=("architecture",),
        selected_profiles=("precommit",),
        selected_checks=("tach",),
        review_categories=("architecture",),
        requirements=(
            RequirementResult(
                rule_id="architecture",
                id="adr",
                mode="required",
                kind="changed-path",
                paths=("docs/architecture/decisions/*.md",),
                minimum=1,
                matched_paths=(),
                status="missing",
                message="Add an ADR.",
            ),
        ),
        recommended_commands=(
            "python -m agent_maintainer verify --profile precommit",
        ),
        advisories=("review ownership",),
        blocking_findings=("architecture/adr: Add an ADR.",),
    )
