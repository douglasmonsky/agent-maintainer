"""Base/current/live contract orchestration tests."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from agent_maintainer.contracts import service
from agent_maintainer.contracts.comparison import compare_descriptors
from agent_maintainer.contracts.git_base import BaseContractState, GitPathChange
from agent_maintainer.contracts.models import (
    ContractBaseline,
    ContractDecision,
    ContractKind,
    ContractPolicy,
    ContractSpec,
    Descriptor,
)
from agent_maintainer.contracts.normalization import build_descriptor


def _spec(
    contract_id: str = "public-api",
    *,
    revision: int = 1,
    kind: ContractKind = "python-api",
) -> ContractSpec:
    return ContractSpec(
        id=contract_id,
        kind=kind,
        owner="agent_maintainer.api",
        stability="beta",
        revision=revision,
        source="src/agent_maintainer/api.py",
        exports=("*",) if kind == "python-api" else (),
        migration_paths=("CHANGELOG.md",),
    )


def _descriptor(spec: ContractSpec, member: str) -> Descriptor:
    return build_descriptor(spec, {"exports": [{"kind": "function", "name": member}]})


def _policy(spec: ContractSpec, *decisions: ContractDecision) -> ContractPolicy:
    return ContractPolicy(contracts=(spec,), decisions=tuple(decisions))


def _baseline(descriptor: Descriptor, version: str) -> ContractBaseline:
    return ContractBaseline(package_version=version, descriptors=(descriptor,))


@dataclass(frozen=True)
class ServiceState:
    """Dependency results for one isolated service orchestration test."""

    current_policy: ContractPolicy
    live: tuple[Descriptor, ...]
    current_baseline: ContractBaseline | None
    base_state: BaseContractState | None
    current_version: str = "0.1.0b10"
    git_changes: tuple[GitPathChange, ...] = ()


def _install_state(
    monkeypatch: pytest.MonkeyPatch,
    state: ServiceState,
) -> None:
    monkeypatch.setattr(service, "load_policy", lambda _root: state.current_policy)
    monkeypatch.setattr(service, "extract_all", lambda _root, _policy: state.live)
    monkeypatch.setattr(service, "load_baseline", lambda _root: state.current_baseline)
    monkeypatch.setattr(
        service,
        "read_package_version",
        lambda _root, _path: state.current_version,
    )
    monkeypatch.setattr(
        service,
        "read_base_contract_files",
        lambda _root, _ref: state.base_state,
    )
    monkeypatch.setattr(
        service,
        "read_git_changes",
        lambda _root, _commit: state.git_changes,
    )


def test_current_baseline_must_exactly_match_live_extraction(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Freshness blocks historical evaluation before a stale snapshot can pass."""
    spec = _spec()
    old = _descriptor(spec, "old")
    new = _descriptor(spec, "new")
    state = BaseContractState(BASE_COMMIT, _policy(spec), _baseline(old, "0.1.0b9"))
    _install_state(
        monkeypatch,
        ServiceState(
            current_policy=_policy(spec),
            live=(new,),
            current_baseline=_baseline(old, "0.1.0b9"),
            base_state=state,
        ),
    )
    report = service.build_contract_report(tmp_path, base_ref="main", mode="check")

    assert report.errors == ("current contract baseline does not match live extraction",)
    assert report.changes == ()
    assert not report.can_snapshot


def test_snapshot_can_replace_stale_baseline_after_obligations_pass(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Snapshot compares base to live while check continues to enforce freshness."""
    base_spec = _spec(revision=1)
    current_spec = _spec(revision=2)
    old = _descriptor(base_spec, "old")
    new = build_descriptor(
        current_spec,
        {"exports": [{"kind": "constant", "name": "new", "value": 1}]},
    )
    state = BaseContractState(
        BASE_COMMIT,
        _policy(base_spec),
        _baseline(old, "0.1.0b9"),
    )
    _install_state(
        monkeypatch,
        ServiceState(
            current_policy=_policy(current_spec),
            live=(new,),
            current_baseline=_baseline(old, "0.1.0b9"),
            base_state=state,
            git_changes=(GitPathChange("CHANGELOG.md", "modified"),),
        ),
    )

    report = service.build_contract_report(tmp_path, base_ref="main", mode="snapshot")

    assert report.errors == ()
    assert any(change.operation == "member-remove" for change in report.changes)
    assert all(item.status == "satisfied" for item in report.obligations)
    assert report.can_snapshot


BASE_COMMIT = "a" * 40


def test_rewriting_current_baseline_cannot_hide_live_break(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Base descriptors are compared directly with live descriptors."""
    base_spec = _spec(revision=1)
    current_spec = _spec(revision=2)
    old = _descriptor(base_spec, "old")
    new = build_descriptor(
        current_spec,
        {"exports": [{"kind": "constant", "name": "new", "value": 1}]},
    )
    state = BaseContractState(
        BASE_COMMIT,
        _policy(base_spec),
        _baseline(old, "0.1.0b9"),
    )
    _install_state(
        monkeypatch,
        ServiceState(
            current_policy=_policy(current_spec),
            live=(new,),
            current_baseline=_baseline(new, "0.1.0b10"),
            base_state=state,
            git_changes=(GitPathChange("CHANGELOG.md", "modified"),),
        ),
    )
    git_reads = 0

    def read_git_changes(_root: Path, _commit: str) -> tuple[GitPathChange, ...]:
        nonlocal git_reads
        git_reads += 1
        return (GitPathChange("CHANGELOG.md", "modified"),)

    monkeypatch.setattr(service, "read_git_changes", read_git_changes)

    report = service.build_contract_report(tmp_path, base_ref="main", mode="check")

    assert any(change.operation == "member-remove" for change in report.changes)
    assert {item.kind for item in report.obligations} == {
        "contract-revision",
        "migration-evidence",
        "package-version",
    }
    assert all(item.status == "satisfied" for item in report.obligations)
    assert git_reads == 1
    assert report.can_snapshot


def test_absent_usable_base_adds_one_advisory_without_retroactive_changes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Fresh current evidence remains useful when history predates adoption."""
    spec = _spec()
    live = _descriptor(spec, "current")
    _install_state(
        monkeypatch,
        ServiceState(
            current_policy=_policy(spec),
            live=(live,),
            current_baseline=_baseline(live, "0.1.0b10"),
            base_state=None,
        ),
    )

    report = service.build_contract_report(tmp_path, base_ref="old", mode="check")

    assert report.base_available is False
    assert report.changes == ()
    assert report.obligations == ()
    assert report.advisories == (service.HISTORICAL_UNAVAILABLE,)
    assert report.can_snapshot


def test_initialization_requires_an_absent_current_baseline(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Initialization is explicit and cannot overwrite existing evidence."""
    spec = _spec()
    live = _descriptor(spec, "current")
    _install_state(
        monkeypatch,
        ServiceState(
            current_policy=_policy(spec),
            live=(live,),
            current_baseline=None,
            base_state=None,
        ),
    )

    initial = service.build_contract_report(
        tmp_path,
        base_ref="old",
        mode="snapshot",
        initialize=True,
    )
    assert initial.can_snapshot
    assert initial.changes == ()
    assert initial.advisories == (service.HISTORICAL_UNAVAILABLE,)

    _install_state(
        monkeypatch,
        ServiceState(
            current_policy=_policy(spec),
            live=(live,),
            current_baseline=_baseline(live, "0.1.0b10"),
            base_state=None,
        ),
    )
    rejected = service.build_contract_report(
        tmp_path,
        base_ref="old",
        mode="snapshot",
        initialize=True,
    )
    assert rejected.errors == ("initialization requires an absent contract baseline",)
    assert not rejected.can_snapshot


def test_missing_baseline_without_initialization_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Ordinary checks never infer initial adoption."""
    spec = _spec()
    live = _descriptor(spec, "current")
    _install_state(
        monkeypatch,
        ServiceState(
            current_policy=_policy(spec),
            live=(live,),
            current_baseline=None,
            base_state=None,
        ),
    )

    report = service.build_contract_report(tmp_path, base_ref="old", mode="check")

    assert report.errors == ("current contract baseline is missing",)


def test_exact_decision_resolves_review_required_change(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Current exact-fingerprint decisions flow through historical comparison."""
    base_spec = _spec(kind="json-schema")
    current_spec = replace(base_spec, revision=1)
    before = build_descriptor(base_spec, {"enum": ["a"]})
    after = build_descriptor(current_spec, {"enum": ["a", "b"]})
    unresolved = compare_descriptors((before,), (after,), ())
    assert unresolved[0].classification == "review-required"
    decision = ContractDecision(
        contract=base_spec.id,
        fingerprint=unresolved[0].fingerprint,
        classification="compatible",
        reason="Consumers tolerate new enum values.",
    )
    current_policy = _policy(current_spec, decision)
    state = BaseContractState(
        BASE_COMMIT,
        _policy(base_spec),
        _baseline(before, "0.1.0b9"),
    )
    _install_state(
        monkeypatch,
        ServiceState(
            current_policy=current_policy,
            live=(after,),
            current_baseline=_baseline(after, "0.1.0b10"),
            base_state=state,
        ),
    )

    report = service.build_contract_report(tmp_path, base_ref="main", mode="check")

    assert report.changes[0].classification == "compatible"
    assert report.decisions == (decision,)
    assert not any(fact.fingerprint == decision.fingerprint for fact in report.repair_facts)


def test_breaking_change_keeps_three_obligations_independent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Revision, package version, and migration evidence fail independently."""
    base_spec = _spec(revision=1)
    current_spec = _spec(revision=1)
    old = _descriptor(base_spec, "old")
    new = build_descriptor(
        current_spec,
        {"exports": [{"kind": "constant", "name": "new", "value": 1}]},
    )
    state = BaseContractState(
        BASE_COMMIT,
        _policy(base_spec),
        _baseline(old, "0.1.0b9"),
    )
    _install_state(
        monkeypatch,
        ServiceState(
            current_policy=_policy(current_spec),
            live=(new,),
            current_baseline=_baseline(new, "0.1.0b9"),
            base_state=state,
            current_version="0.1.0b9",
        ),
    )

    report = service.build_contract_report(tmp_path, base_ref="main", mode="check")

    unresolved = tuple(item for item in report.obligations if item.status == "unresolved")
    assert {item.kind for item in unresolved} == {
        "contract-revision",
        "migration-evidence",
        "package-version",
    }
    assert {fact.kind for fact in report.repair_facts} == {
        "contract-revision",
        "migration-evidence",
        "package-version",
    }
    assert not report.can_snapshot


def test_unresolved_findings_produce_sorted_exact_repair_facts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Every unresolved change or obligation yields one stable repair packet."""
    base_spec = _spec(contract_id="z-api", kind="json-schema")
    current_spec = replace(base_spec, revision=1)
    before = build_descriptor(base_spec, {"enum": ["a"]})
    after = build_descriptor(current_spec, {"enum": ["a", "b"]})
    state = BaseContractState(
        BASE_COMMIT,
        _policy(base_spec),
        _baseline(before, "0.1.0b9"),
    )
    _install_state(
        monkeypatch,
        ServiceState(
            current_policy=_policy(current_spec),
            live=(after,),
            current_baseline=_baseline(after, "0.1.0b9"),
            base_state=state,
        ),
    )

    report = service.build_contract_report(tmp_path, base_ref="main", mode="check")

    assert report.unresolved
    assert report.repair_facts == tuple(
        sorted(
            report.repair_facts,
            key=lambda item: (item.contract_id, item.fingerprint, item.summary),
        )
    )
    assert any(fact.fingerprint == report.changes[0].fingerprint for fact in report.repair_facts)
    assert all(
        "agent-maintainer contract diff" in fact.inspect_command
        for fact in report.repair_facts
    )
