"""Diff-aware verification planning over repository and policy facts."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from agent_maintainer import models as check_models
from agent_maintainer.assess.evidence import collect_evidence
from agent_maintainer.catalogs.catalog import make_checks
from agent_maintainer.config.loader import load_config
from agent_maintainer.ecosystems.file_changes import ChangedPath, classify_changed_paths
from agent_maintainer.ecosystems.git_changes import GitPathChange, run_git_name_status
from agent_maintainer.ecosystems.models import ChangeKind, FileChangeClassification
from agent_maintainer.verification_plan.matching import path_matches
from agent_maintainer.verification_plan.models import (
    AffectedUnit,
    PathClassification,
    PathRiskPolicy,
    PathRiskRule,
    PlannedChange,
    RequirementResult,
    VerificationPlanReport,
)
from agent_maintainer.verification_plan.policy import (
    PolicyError,
    load_policy,
    validate_catalog_names,
)
from agent_maintainer.verification_plan.units import (
    UnitResolutionInputs,
    resolve_affected_units,
)

DEFAULT_POLICY_PATH = Path(".agent-maintainer/path-risk.toml")


@dataclass(frozen=True)
class PlanningFacts:
    """Already-collected facts consumed by the pure planning core."""

    target: Path
    base_ref: str
    staged: bool
    changes: tuple[GitPathChange, ...] = ()
    classifications: tuple[FileChangeClassification, ...] = ()
    affected_units: tuple[AffectedUnit, ...] = ()
    unit_advisories: tuple[str, ...] = ()
    policy: PathRiskPolicy | None = None
    catalog_profiles: frozenset[str] = frozenset()
    catalog_checks: tuple[str, ...] = ()
    policy_path: Path = DEFAULT_POLICY_PATH


def build_verification_plan(
    target: Path,
    *,
    base_ref: str,
    staged: bool,
    policy_path: Path = DEFAULT_POLICY_PATH,
) -> VerificationPlanReport:
    """Collect bounded repository facts and build one verification plan."""
    root = target.resolve()
    config = load_config(root)
    changes = run_git_name_status(base_ref, staged=staged, cwd=root)
    classifications = classify_changed_paths(
        tuple(
            ChangedPath(path, _change_kind(change.kind))
            for change in changes
            for path in change.affected_paths()
        ),
        config,
        repo_root=root,
    )
    evidence = collect_evidence(root)
    affected_units, unit_advisories = resolve_affected_units(
        root,
        changes=changes,
        inputs=UnitResolutionInputs(
            config=config,
            classifications=classifications,
            package_workspace=evidence.package_workspace,
            java_module_paths=evidence.java_module_paths,
        ),
    )
    configured_checks = make_checks(config, base_ref, base_ref, staged=staged)
    load_path = policy_path if policy_path.is_absolute() else root / policy_path
    policy = load_policy(load_path)
    return plan_from_facts(
        PlanningFacts(
            target=root,
            base_ref=base_ref,
            staged=staged,
            changes=changes,
            classifications=classifications,
            affected_units=affected_units,
            unit_advisories=unit_advisories,
            policy=policy,
            policy_path=policy_path,
            catalog_profiles=check_models.VALID_PROFILES,
            catalog_checks=_configured_check_names(configured_checks),
        ),
    )


def plan_from_facts(facts: PlanningFacts) -> VerificationPlanReport:
    """Build a deterministic plan from already-collected repository facts."""
    validate_catalog_names(
        facts.policy or PathRiskPolicy(path=facts.policy_path.as_posix()),
        profiles=facts.catalog_profiles,
        checks=facts.catalog_checks,
    )
    planned_changes = _planned_changes(facts.changes, facts.classifications)
    if facts.policy is None:
        return VerificationPlanReport(
            target=str(facts.target),
            base_ref=facts.base_ref,
            staged=facts.staged,
            policy_path=facts.policy_path.as_posix(),
            policy_configured=False,
            changes=planned_changes,
            affected_units=tuple(sorted(facts.affected_units, key=_unit_sort_key)),
            advisories=tuple(sorted(set(facts.unit_advisories))),
        )

    affected_paths = tuple(
        sorted({path for change in facts.changes for path in change.affected_paths()}),
    )
    evidence_paths = tuple(
        sorted({path for change in facts.changes for path in change.evidence_paths()}),
    )
    matched_rules = tuple(
        rule
        for rule in facts.policy.rules
        if any(path_matches(pattern, path) for pattern in rule.paths for path in affected_paths)
    )
    requirements = _requirements(matched_rules, evidence_paths)
    advisories = set(facts.unit_advisories)
    blockers: set[str] = set()
    for requirement in requirements:
        if requirement.status == "satisfied":
            continue
        finding = f"{requirement.rule_id}/{requirement.id}: {requirement.message}"
        (blockers if requirement.mode == "required" else advisories).add(finding)
    profiles = _union(rule.profiles for rule in matched_rules)
    return VerificationPlanReport(
        target=str(facts.target),
        base_ref=facts.base_ref,
        staged=facts.staged,
        policy_path=facts.policy.path,
        policy_configured=True,
        changes=planned_changes,
        affected_units=tuple(sorted(facts.affected_units, key=_unit_sort_key)),
        matched_rules=tuple(sorted(rule.id for rule in matched_rules)),
        selected_profiles=profiles,
        selected_checks=_union(rule.checks for rule in matched_rules),
        review_categories=_union(rule.review_categories for rule in matched_rules),
        requirements=requirements,
        recommended_commands=tuple(
            f"python -m agent_maintainer verify --profile {profile}" for profile in profiles
        ),
        advisories=tuple(sorted(advisories)),
        blocking_findings=tuple(sorted(blockers)),
    )


def _requirements(
    rules: Sequence[PathRiskRule],
    evidence_paths: tuple[str, ...],
) -> tuple[RequirementResult, ...]:
    results: list[RequirementResult] = []
    for rule in rules:
        for requirement in rule.evidence:
            matched = tuple(
                path
                for path in evidence_paths
                if any(path_matches(pattern, path) for pattern in requirement.paths)
            )
            message = requirement.message or (
                f"Provide at least {requirement.minimum} changed path(s) matching "
                f"{', '.join(requirement.paths)}."
            )
            results.append(
                RequirementResult(
                    rule_id=rule.id,
                    id=requirement.id,
                    mode=rule.mode,
                    kind=requirement.kind,
                    paths=requirement.paths,
                    minimum=requirement.minimum,
                    matched_paths=matched,
                    status=("satisfied" if len(matched) >= requirement.minimum else "missing"),
                    message=message,
                ),
            )
    return tuple(sorted(results, key=lambda item: (item.rule_id, item.id)))


def _planned_changes(
    changes: Sequence[GitPathChange],
    classifications: Sequence[FileChangeClassification],
) -> tuple[PlannedChange, ...]:
    by_path: dict[str, list[FileChangeClassification]] = {}
    for classification in classifications:
        by_path.setdefault(classification.path, []).append(classification)
    planned: list[PlannedChange] = []
    for change in changes:
        attached: list[PathClassification] = []
        for path in change.affected_paths():
            relation = _relation(change, path)
            for classification in by_path.get(path, ()):
                attached.append(
                    PathClassification(
                        path=path,
                        relation=relation,
                        ecosystem=classification.ecosystem,
                        role=classification.role.value,
                        generated=classification.generated,
                        ignored=classification.ignored,
                    ),
                )
        planned.append(
            PlannedChange(
                path=change.path,
                kind=change.kind,
                old_path=change.old_path,
                classifications=tuple(
                    sorted(attached, key=lambda item: (item.path, item.ecosystem, item.role))
                ),
            ),
        )
    return tuple(sorted(planned, key=lambda item: (item.path, item.old_path or "", item.kind)))


def _relation(change: GitPathChange, path: str) -> str:
    if change.old_path is None:
        return "current"
    return "source" if path == change.old_path else "destination"


def _change_kind(value: str) -> ChangeKind:
    try:
        return ChangeKind(value)
    except ValueError:
        return ChangeKind.UNKNOWN


def _configured_check_names(
    checks: Sequence[check_models.Check],
) -> tuple[str, ...]:
    """Collapse disjoint profile variants while rejecting ambiguous duplicates."""
    profiles_by_name: dict[str, set[str]] = {}
    for check in checks:
        configured_profiles = profiles_by_name.setdefault(check.name, set())
        overlap = configured_profiles.intersection(check.profiles)
        if overlap:
            profile = sorted(overlap)[0]
            raise PolicyError(
                f"duplicate configured check {check.name!r} for profile {profile!r}",
            )
        configured_profiles.update(check.profiles)
    return tuple(sorted(profiles_by_name))


def _union(groups: Iterable[tuple[str, ...]]) -> tuple[str, ...]:
    return tuple(sorted({item for group in groups for item in group}))


def _unit_sort_key(unit: AffectedUnit) -> tuple[int, str, str]:
    return (0 if unit.kind == "repository" else 1, unit.kind, unit.root)
