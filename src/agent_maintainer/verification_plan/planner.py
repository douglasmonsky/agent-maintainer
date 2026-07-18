"""Diff-aware verification planning over repository and policy facts."""

from __future__ import annotations

from collections import abc
from dataclasses import dataclass
from pathlib import Path

from agent_maintainer import models as check_models
from agent_maintainer.assess import evidence as assess_evidence
from agent_maintainer.catalogs import catalog
from agent_maintainer.config import loader
from agent_maintainer.ecosystems import file_changes, git_changes
from agent_maintainer.ecosystems import models as ecosystem_models
from agent_maintainer.verification_plan import matching, policy, units
from agent_maintainer.verification_plan import models as plan_models

DEFAULT_POLICY_PATH = Path(".agent-maintainer/path-risk.toml")


@dataclass(frozen=True)
class PlanningFacts:
    """Already-collected facts consumed by the pure planning core."""

    target: Path
    base_ref: str
    staged: bool
    changes: tuple[git_changes.GitPathChange, ...] = ()
    classifications: tuple[ecosystem_models.FileChangeClassification, ...] = ()
    affected_units: tuple[plan_models.AffectedUnit, ...] = ()
    unit_advisories: tuple[str, ...] = ()
    policy: plan_models.PathRiskPolicy | None = None
    catalog_profiles: frozenset[str] = frozenset()
    catalog_checks: tuple[str, ...] = ()
    policy_path: Path = DEFAULT_POLICY_PATH


# docsync:evidence.start evidence.readme.verification_planning
def build_verification_plan(
    target: Path,
    *,
    base_ref: str,
    staged: bool,
    policy_path: Path = DEFAULT_POLICY_PATH,
) -> plan_models.VerificationPlanReport:
    """Collect bounded repository facts and build one verification plan."""
    root = target.resolve()
    if not root.is_dir():
        raise RuntimeError(f"target must be an existing directory: {target}")
    config = loader.load_config(root)
    changes = git_changes.run_git_name_status(base_ref, staged=staged, cwd=root)
    classifications = file_changes.classify_changed_paths(
        tuple(
            file_changes.ChangedPath(path, _change_kind(change.kind))
            for change in changes
            for path in change.affected_paths()
        ),
        config,
        repo_root=root,
    )
    evidence = assess_evidence.collect_evidence(root)
    affected_units, unit_advisories = units.resolve_affected_units(
        root,
        changes=changes,
        inputs=units.UnitResolutionInputs(
            config=config,
            classifications=classifications,
            package_workspace=evidence.package_workspace,
            java_module_paths=evidence.java_module_paths,
        ),
    )
    configured_checks = catalog.make_checks(config, base_ref, base_ref, staged=staged)
    load_path = policy_path if policy_path.is_absolute() else root / policy_path
    configured_policy = policy.load_policy(load_path)
    return plan_from_facts(
        PlanningFacts(
            target=root,
            base_ref=base_ref,
            staged=staged,
            changes=changes,
            classifications=classifications,
            affected_units=affected_units,
            unit_advisories=unit_advisories,
            policy=configured_policy,
            policy_path=policy_path,
            catalog_profiles=check_models.VALID_PROFILES,
            catalog_checks=_configured_check_names(configured_checks),
        ),
    )


def plan_from_facts(facts: PlanningFacts) -> plan_models.VerificationPlanReport:
    """Build a deterministic plan from already-collected repository facts."""
    policy.validate_catalog_names(
        facts.policy or plan_models.PathRiskPolicy(path=facts.policy_path.as_posix()),
        profiles=facts.catalog_profiles,
        checks=facts.catalog_checks,
    )
    planned_changes = _planned_changes(facts.changes, facts.classifications)
    if facts.policy is None:
        return _unconfigured_report(facts, planned_changes)
    return _configured_report(facts, planned_changes)


def _unconfigured_report(
    facts: PlanningFacts,
    planned_changes: tuple[plan_models.PlannedChange, ...],
) -> plan_models.VerificationPlanReport:
    return plan_models.VerificationPlanReport(
        target=str(facts.target),
        base_ref=facts.base_ref,
        staged=facts.staged,
        policy_path=facts.policy_path.as_posix(),
        policy_configured=False,
        changes=planned_changes,
        affected_units=tuple(sorted(facts.affected_units, key=_unit_sort_key)),
        advisories=tuple(sorted(set(facts.unit_advisories))),
    )


def _configured_report(
    facts: PlanningFacts,
    planned_changes: tuple[plan_models.PlannedChange, ...],
) -> plan_models.VerificationPlanReport:
    configured_policy = facts.policy
    if configured_policy is None:
        raise RuntimeError("configured report requires policy facts")
    affected_paths = _paths_for_changes(facts.changes, evidence_only=False)
    evidence_paths = _paths_for_changes(facts.changes, evidence_only=True)
    matched_rules = _matched_rules(
        configured_policy.rules,
        affected_paths,
    )
    requirements = _requirements(matched_rules, evidence_paths)
    advisories = set(facts.unit_advisories)
    blockers: set[str] = set()
    _classify_findings(requirements, advisories=advisories, blockers=blockers)
    profiles = _union(rule.profiles for rule in matched_rules)
    return plan_models.VerificationPlanReport(
        target=str(facts.target),
        base_ref=facts.base_ref,
        staged=facts.staged,
        policy_path=configured_policy.path,
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


def _paths_for_changes(
    changes: tuple[git_changes.GitPathChange, ...],
    *,
    evidence_only: bool,
) -> tuple[str, ...]:
    path_groups = (
        (change.evidence_paths() if evidence_only else change.affected_paths())
        for change in changes
    )
    return tuple(sorted({path for paths in path_groups for path in paths}))


def _matched_rules(
    rules: tuple[plan_models.PathRiskRule, ...],
    affected_paths: tuple[str, ...],
) -> tuple[plan_models.PathRiskRule, ...]:
    return tuple(
        rule
        for rule in rules
        if any(
            matching.path_matches(pattern, path)
            for pattern in rule.paths
            for path in affected_paths
        )
    )


def _classify_findings(
    requirements: tuple[plan_models.RequirementResult, ...],
    *,
    advisories: set[str],
    blockers: set[str],
) -> None:
    for requirement in requirements:
        if requirement.status == "satisfied":
            continue
        finding = f"{requirement.rule_id}/{requirement.id}: {requirement.message}"
        destination = blockers if requirement.mode == "required" else advisories
        destination.add(finding)


def _requirements(
    rules: abc.Sequence[plan_models.PathRiskRule],
    evidence_paths: tuple[str, ...],
) -> tuple[plan_models.RequirementResult, ...]:
    results: list[plan_models.RequirementResult] = []
    for rule in rules:
        for requirement in rule.evidence:
            results.append(_requirement_result(rule, requirement, evidence_paths))
    return tuple(sorted(results, key=lambda item: (item.rule_id, item.id)))


def _requirement_result(
    rule: plan_models.PathRiskRule,
    requirement: plan_models.EvidenceRequirement,
    evidence_paths: tuple[str, ...],
) -> plan_models.RequirementResult:
    matched = tuple(
        path
        for path in evidence_paths
        if any(matching.path_matches(pattern, path) for pattern in requirement.paths)
    )
    return plan_models.RequirementResult(
        rule_id=rule.id,
        id=requirement.id,
        mode=rule.mode,
        kind=requirement.kind,
        paths=requirement.paths,
        minimum=requirement.minimum,
        matched_paths=matched,
        status=("satisfied" if len(matched) >= requirement.minimum else "missing"),
        message=requirement.message or _missing_evidence_message(requirement),
    )


def _missing_evidence_message(requirement: plan_models.EvidenceRequirement) -> str:
    patterns = ", ".join(requirement.paths)
    return f"Provide at least {requirement.minimum} changed path(s) matching {patterns}."


def _planned_changes(
    changes: abc.Sequence[git_changes.GitPathChange],
    classifications: abc.Sequence[ecosystem_models.FileChangeClassification],
) -> tuple[plan_models.PlannedChange, ...]:
    by_path: dict[str, list[ecosystem_models.FileChangeClassification]] = {}
    for classification in classifications:
        by_path.setdefault(classification.path, []).append(classification)
    planned = tuple(_planned_change(change, by_path) for change in changes)
    return tuple(sorted(planned, key=_planned_change_sort_key))


def _planned_change(
    change: git_changes.GitPathChange,
    by_path: dict[str, list[ecosystem_models.FileChangeClassification]],
) -> plan_models.PlannedChange:
    attached = tuple(
        plan_models.PathClassification(
            path=path,
            relation=_relation(change, path),
            ecosystem=classification.ecosystem,
            role=classification.role.value,
            generated=classification.generated,
            ignored=classification.ignored,
        )
        for path in change.affected_paths()
        for classification in by_path.get(path, ())
    )
    return plan_models.PlannedChange(
        path=change.path,
        kind=change.kind,
        old_path=change.old_path,
        classifications=tuple(
            sorted(attached, key=lambda item: (item.path, item.ecosystem, item.role))
        ),
    )


def _relation(change: git_changes.GitPathChange, path: str) -> str:
    if change.old_path is None:
        return "current"
    return "source" if path == change.old_path else "destination"


def _change_kind(value: str) -> ecosystem_models.ChangeKind:
    try:
        return ecosystem_models.ChangeKind(value)
    except ValueError:
        return ecosystem_models.ChangeKind.UNKNOWN


def _configured_check_names(
    checks: abc.Sequence[check_models.Check],
) -> tuple[str, ...]:
    """Collapse disjoint profile variants while rejecting ambiguous duplicates."""
    profiles_by_name: dict[str, set[str]] = {}
    for check in checks:
        configured_profiles = profiles_by_name.setdefault(check.name, set())
        overlap = configured_profiles.intersection(check.profiles)
        if overlap:
            profile = sorted(overlap)[0]
            raise policy.PolicyError(
                f"duplicate configured check {check.name!r} for profile {profile!r}",
            )
        configured_profiles.update(check.profiles)
    return tuple(sorted(profiles_by_name))


def _union(groups: abc.Iterable[tuple[str, ...]]) -> tuple[str, ...]:
    return tuple(sorted({item for group in groups for item in group}))


def _unit_sort_key(unit: plan_models.AffectedUnit) -> tuple[int, str, str]:
    return (0 if unit.kind == "repository" else 1, unit.kind, unit.root)


def _planned_change_sort_key(item: plan_models.PlannedChange) -> tuple[str, str, str]:
    return (item.path, item.old_path or "", item.kind)


# docsync:evidence.end evidence.readme.verification_planning
