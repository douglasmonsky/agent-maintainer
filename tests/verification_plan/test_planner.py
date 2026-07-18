"""Pure diff-aware verification planning tests."""

from __future__ import annotations

from pathlib import Path

from agent_maintainer.ecosystems.git_changes import GitPathChange
from agent_maintainer.ecosystems.models import (
    ChangeKind,
    FileChangeClassification,
    FileRole,
)
from agent_maintainer.verification_plan.models import (
    AffectedUnit,
    EvidenceRequirement,
    PathRiskPolicy,
    PathRiskRule,
)
from agent_maintainer.verification_plan.planner import PlanningFacts, plan_from_facts


def test_overlapping_rules_union_and_sort_all_selections() -> None:
    report = plan_from_facts(
        PlanningFacts(
            target=Path("/repo"),
            base_ref="origin/main",
            staged=False,
            changes=(GitPathChange("src/app.py", "modified"),),
            classifications=(_classification("src/app.py", generated=True),),
            affected_units=(AffectedUnit("python-package", "app", "src", ("src/app.py",)),),
            unit_advisories=("unit note",),
            policy=PathRiskPolicy(
                path=".agent-maintainer/path-risk.toml",
                rules=(
                    PathRiskRule(
                        id="source",
                        paths=("src/**",),
                        profiles=("precommit", "fast"),
                        checks=("tach", "ruff"),
                        review_categories=("correctness",),
                    ),
                    PathRiskRule(
                        id="python",
                        paths=("**/*.py",),
                        profiles=("fast",),
                        checks=("ruff",),
                        review_categories=("architecture",),
                    ),
                ),
            ),
            catalog_profiles=frozenset(("precommit", "fast")),
            catalog_checks=("tach", "ruff"),
        ),
    )

    assert report.matched_rules == ("python", "source")
    assert report.selected_profiles == ("fast", "precommit")
    assert report.selected_checks == ("ruff", "tach")
    assert report.review_categories == ("architecture", "correctness")
    assert report.recommended_commands == (
        "python -m agent_maintainer verify --profile fast",
        "python -m agent_maintainer verify --profile precommit",
    )
    assert report.advisories == ("unit note",)
    assert report.changes[0].classifications[0].generated is True


def test_required_missing_evidence_blocks_but_advisory_only_warns() -> None:
    report = plan_from_facts(
        PlanningFacts(
            target=Path("/repo"),
            base_ref="origin/main",
            staged=False,
            changes=(GitPathChange("tach.toml", "modified"),),
            classifications=(),
            affected_units=(),
            unit_advisories=(),
            policy=PathRiskPolicy(
                path="policy.toml",
                rules=(
                    _rule_with_evidence(
                        "architecture-policy",
                        "required",
                        "architecture-decision",
                        ("docs/architecture/decisions/*.md",),
                        "Add or update an architecture decision record.",
                    ),
                    _rule_with_evidence(
                        "docs-guidance",
                        "advisory",
                        "docs-note",
                        ("docs/*.md",),
                        "Update relevant documentation.",
                    ),
                ),
            ),
            catalog_profiles=frozenset(),
            catalog_checks=(),
        ),
    )

    assert report.blocking_findings == (
        "architecture-policy/architecture-decision: Add or update an architecture decision record.",
    )
    assert report.advisories == ("docs-guidance/docs-note: Update relevant documentation.",)
    assert [requirement.status for requirement in report.requirements] == [
        "missing",
        "missing",
    ]


def test_rule_local_minimum_and_destination_only_evidence() -> None:
    report = plan_from_facts(
        PlanningFacts(
            target=Path("/repo"),
            base_ref="main",
            staged=False,
            changes=(
                GitPathChange(
                    "docs/architecture/decisions/new.md",
                    "renamed",
                    old_path="src/security/old.py",
                ),
                GitPathChange("docs/architecture/decisions/second.md", "added"),
                GitPathChange("docs/removed.md", "deleted"),
            ),
            classifications=(),
            affected_units=(),
            unit_advisories=(),
            policy=PathRiskPolicy(
                path="policy.toml",
                rules=(
                    PathRiskRule(
                        id="security",
                        paths=("src/security/**",),
                        mode="required",
                        evidence=(
                            EvidenceRequirement(
                                id="decisions",
                                kind="changed-path",
                                paths=("docs/architecture/decisions/*.md",),
                                minimum=2,
                                message="Add two decisions.",
                            ),
                            EvidenceRequirement(
                                id="removed-doc",
                                kind="changed-path",
                                paths=("docs/removed.md",),
                                message="Restore the removed document.",
                            ),
                        ),
                    ),
                ),
            ),
            catalog_profiles=frozenset(),
            catalog_checks=(),
        ),
    )

    assert report.matched_rules == ("security",)
    assert report.requirements[0].matched_paths == (
        "docs/architecture/decisions/new.md",
        "docs/architecture/decisions/second.md",
    )
    assert report.requirements[0].status == "satisfied"
    assert report.requirements[1].matched_paths == ()
    assert report.requirements[1].status == "missing"


def test_ignored_classification_does_not_suppress_rule_matching() -> None:
    report = plan_from_facts(
        PlanningFacts(
            target=Path("/repo"),
            base_ref="main",
            staged=True,
            changes=(GitPathChange("generated/secret.pem", "added"),),
            classifications=(_classification("generated/secret.pem", ignored=True),),
            affected_units=(),
            unit_advisories=(),
            policy=PathRiskPolicy(
                path="policy.toml",
                rules=(PathRiskRule(id="secrets", paths=("**/*.pem",)),),
            ),
            catalog_profiles=frozenset(),
            catalog_checks=(),
        ),
    )

    assert report.matched_rules == ("secrets",)
    assert report.changes[0].classifications[0].ignored is True


def test_absent_policy_returns_stable_unconfigured_report() -> None:
    report = plan_from_facts(
        PlanningFacts(
            target=Path("/repo"),
            base_ref="main",
            staged=False,
            changes=(GitPathChange("README.md", "modified"),),
            classifications=(),
            affected_units=(),
            unit_advisories=(),
            policy=None,
            policy_path=Path(".agent-maintainer/path-risk.toml"),
            catalog_profiles=frozenset(("fast",)),
            catalog_checks=("ruff",),
        ),
    )

    assert report.policy_configured is False
    assert report.policy_path == ".agent-maintainer/path-risk.toml"
    assert report.matched_rules == ()
    assert report.recommended_commands == ()


def _rule_with_evidence(
    rule_id: str,
    mode: str,
    evidence_id: str,
    paths: tuple[str, ...],
    message: str,
) -> PathRiskRule:
    return PathRiskRule(
        id=rule_id,
        paths=("tach.toml",),
        mode=mode,
        evidence=(
            EvidenceRequirement(
                id=evidence_id,
                kind="changed-path",
                paths=paths,
                message=message,
            ),
        ),
    )


def _classification(
    path: str,
    *,
    generated: bool = False,
    ignored: bool = False,
) -> FileChangeClassification:
    return FileChangeClassification(
        path=path,
        ecosystem="python",
        role=FileRole.GENERATED if generated else FileRole.SOURCE,
        change_kind=ChangeKind.ADDED,
        generated=generated,
        ignored=ignored,
    )
