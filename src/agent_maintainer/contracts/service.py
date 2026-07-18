"""Base/current/live orchestration for semantic contract ratchets."""

from __future__ import annotations

import shlex
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from agent_maintainer.contracts import baseline, comparison, extraction
from agent_maintainer.contracts import models as contract_models
from agent_maintainer.contracts import policy as policy_module
from agent_maintainer.contracts.git_base import (
    BaseContractState,
    GitPathChange,
    read_base_contract_files,
    read_git_changes,
)
from agent_maintainer.contracts.migrations import migration_obligations
from agent_maintainer.contracts.models import (
    ContractBaseline,
    ContractChange,
    ContractDecision,
    ContractError,
    ContractObligation,
    ContractPolicy,
    ContractReport,
    Descriptor,
)
from agent_maintainer.contracts.versioning import (
    contract_revision_obligations,
    package_version_obligation,
    read_package_version,
)

HISTORICAL_UNAVAILABLE = "historical contract compatibility is unavailable for the selected base"
VALID_MODES = frozenset(("check", "diff", "snapshot"))
extract_all = extraction.extract_all
load_baseline = baseline.load_baseline
load_policy = policy_module.load_policy


@dataclass(frozen=True)
class _CurrentState:
    policy: ContractPolicy
    descriptors: tuple[Descriptor, ...]
    package_version: str
    baseline: ContractBaseline | None


@dataclass(frozen=True)
class _ReportContext:
    mode: str
    base_ref: str
    package_version: str
    descriptors: tuple[Descriptor, ...]
    decisions: tuple[ContractDecision, ...]

    def report(self) -> ContractReport:
        return ContractReport(
            mode=self.mode,
            base_ref=self.base_ref,
            current_package_version=self.package_version,
            descriptors=self.descriptors,
            decisions=self.decisions,
        )


def build_contract_report(
    repo_root: Path,
    *,
    base_ref: str,
    mode: str,
    initialize: bool = False,
) -> ContractReport:
    """Build one deterministic three-way contract compatibility report."""

    root = repo_root.resolve()
    if mode not in VALID_MODES:
        return ContractReport(mode=mode, base_ref=base_ref, errors=("invalid contract mode",))
    try:
        current = _load_current(root)
    except (ContractError, OSError, ValueError) as exc:
        return _invalid_report(mode, base_ref, str(exc))
    context = _report_context(mode, base_ref, current)
    invalid_current = _current_state_error(context, current, initialize=initialize)
    if invalid_current is not None:
        return invalid_current
    try:
        base = read_base_contract_files(root, base_ref)
    except (ContractError, OSError, ValueError) as exc:
        return replace(context.report(), errors=(str(exc),))
    if base is None:
        report = replace(
            context.report(),
            advisories=(HISTORICAL_UNAVAILABLE,),
            can_snapshot=True,
        )
    else:
        report = _historical_report(root, current, base, context)
    return report


def _historical_report(
    repo_root: Path,
    current: _CurrentState,
    base: BaseContractState,
    context: _ReportContext,
) -> ContractReport:
    changes = comparison.compare_descriptors(
        base.baseline.descriptors,
        current.descriptors,
        current.policy.decisions,
    )
    try:
        obligations = _historical_obligations(repo_root, current, base, changes)
    except (ContractError, OSError, ValueError) as exc:
        return replace(
            context.report(),
            base_available=True,
            base_package_version=base.baseline.package_version,
            changes=changes,
            errors=(str(exc),),
        )
    repair_facts = _repair_facts(changes, obligations, context.base_ref)
    report = replace(
        context.report(),
        base_available=True,
        base_package_version=base.baseline.package_version,
        changes=changes,
        obligations=obligations,
        repair_facts=repair_facts,
    )
    return replace(report, can_snapshot=not report.unresolved)


def _historical_obligations(
    repo_root: Path,
    current: _CurrentState,
    base: BaseContractState,
    changes: Sequence[ContractChange],
) -> tuple[ContractObligation, ...]:
    git_changes = read_git_changes(repo_root, base.commit)
    return _obligations(
        base,
        current.policy,
        current.package_version,
        changes,
        git_changes,
    )


def _load_current(repo_root: Path) -> _CurrentState:
    current_policy = load_policy(repo_root)
    if current_policy is None:
        raise ContractError("current contract policy is missing")
    return _CurrentState(
        policy=current_policy,
        descriptors=_sorted_descriptors(extract_all(repo_root, current_policy)),
        package_version=read_package_version(repo_root, current_policy.package_version_file),
        baseline=load_baseline(repo_root),
    )


def _report_context(mode: str, base_ref: str, current: _CurrentState) -> _ReportContext:
    return _ReportContext(
        mode=mode,
        base_ref=base_ref,
        package_version=current.package_version,
        descriptors=current.descriptors,
        decisions=_sorted_decisions(current.policy),
    )


def _current_state_error(
    context: _ReportContext,
    current: _CurrentState,
    *,
    initialize: bool,
) -> ContractReport | None:
    if initialize and current.baseline is not None:
        return replace(
            context.report(),
            errors=("initialization requires an absent contract baseline",),
        )
    if initialize:
        return replace(
            context.report(),
            advisories=(HISTORICAL_UNAVAILABLE,),
            can_snapshot=True,
        )
    if current.baseline is None:
        return replace(
            context.report(),
            errors=("current contract baseline is missing",),
        )
    if context.mode != "snapshot" and not _baseline_is_fresh(
        current.baseline.descriptors,
        current.descriptors,
    ):
        return replace(
            context.report(),
            errors=("current contract baseline does not match live extraction",),
        )
    return None


def _obligations(
    base: BaseContractState,
    policy: ContractPolicy,
    current_version: str,
    changes: Sequence[ContractChange],
    git_changes: Sequence[GitPathChange],
) -> tuple[ContractObligation, ...]:
    obligations = (
        *contract_revision_obligations(base.policy, policy, changes),
        package_version_obligation(
            base.baseline.package_version,
            current_version,
            policy,
            changes,
        ),
        *migration_obligations(policy, changes, git_changes),
    )
    return tuple(sorted(obligations, key=_obligation_key))


def _repair_facts(
    changes: Sequence[ContractChange],
    obligations: Sequence[ContractObligation],
    base_ref: str,
) -> tuple[contract_models.RepairFact, ...]:
    command = f"agent-maintainer contract diff --base-ref {shlex.quote(base_ref)} --json"
    facts = [
        contract_models.RepairFact(
            contract_id=change.contract_id,
            fingerprint=change.fingerprint,
            summary=f"review required for {change.operation} at {change.path}",
            inspect_command=command,
        )
        for change in changes
        if change.classification == "review-required"
    ]
    facts.extend(
        contract_models.RepairFact(
            contract_id=obligation.contract_id or "package",
            fingerprint=_obligation_fingerprint(obligation),
            summary=obligation.message,
            inspect_command=command,
            kind=obligation.kind,
        )
        for obligation in obligations
        if obligation.status == "unresolved"
    )
    return tuple(sorted(facts, key=lambda item: (item.contract_id, item.fingerprint, item.summary)))


def _obligation_fingerprint(obligation: ContractObligation) -> str:
    if len(obligation.fingerprints) == 1:
        return obligation.fingerprints[0]
    return baseline.fingerprint(
        {
            "contract_id": obligation.contract_id,
            "current": obligation.current,
            "expected": obligation.expected,
            "fingerprints": list(obligation.fingerprints),
            "kind": obligation.kind,
            "missing_paths": list(obligation.missing_paths),
        }
    )


def _baseline_is_fresh(
    expected: Sequence[Descriptor],
    descriptors: Sequence[Descriptor],
) -> bool:
    return tuple(item.fingerprint for item in expected) == tuple(
        item.fingerprint for item in descriptors
    )


def _sorted_descriptors(descriptors: Sequence[Descriptor]) -> tuple[Descriptor, ...]:
    return tuple(sorted(descriptors, key=lambda item: item.contract_id))


def _sorted_decisions(policy: ContractPolicy) -> tuple[ContractDecision, ...]:
    return tuple(sorted(policy.decisions, key=lambda item: (item.contract, item.fingerprint)))


def _obligation_key(item: ContractObligation) -> tuple[str, str, str, str]:
    return (item.contract_id, item.kind, item.current, item.expected)


def _invalid_report(mode: str, base_ref: str, message: str) -> ContractReport:
    return ContractReport(mode=mode, base_ref=base_ref, errors=(message,))
