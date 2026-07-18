"""Snapshot authorization regressions for contract ratchets."""

from pathlib import Path
from typing import Never

import pytest

from agent_maintainer.contracts import service
from agent_maintainer.contracts.git_base import BaseContractState
from agent_maintainer.contracts.models import (
    ContractBaseline,
    ContractError,
    ContractPolicy,
    ContractSpec,
    Descriptor,
)
from agent_maintainer.contracts.normalization import build_descriptor


def _spec() -> ContractSpec:
    return ContractSpec(
        id="public-api",
        kind="python-api",
        owner="example.api",
        stability="beta",
        revision=1,
        source="src/example/api.py",
        exports=("*",),
    )


def _install_state(
    monkeypatch: pytest.MonkeyPatch,
    policy: ContractPolicy,
    live: tuple[Descriptor, ...],
    baseline: ContractBaseline | None,
) -> None:
    def load_policy(_root: Path) -> ContractPolicy:
        return policy

    def extract_all(_root: Path, _policy: ContractPolicy) -> tuple[Descriptor, ...]:
        return live

    def load_baseline(_root: Path) -> ContractBaseline | None:
        return baseline

    def read_version(_root: Path, _path: str) -> str:
        return "0.1.0b10"

    def read_base(_root: Path, _ref: str) -> BaseContractState | None:
        return None

    monkeypatch.setattr(service, "load_policy", load_policy)
    monkeypatch.setattr(service, "extract_all", extract_all)
    monkeypatch.setattr(service, "load_baseline", load_baseline)
    monkeypatch.setattr(service, "read_package_version", read_version)
    monkeypatch.setattr(service, "read_base_contract_files", read_base)


def test_snapshot_cannot_replace_existing_baseline_without_historical_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A pre-adoption base cannot turn snapshot into a broad acceptance path."""
    spec = _spec()
    policy = ContractPolicy(contracts=(spec,))
    old = build_descriptor(spec, {"exports": [{"kind": "function", "name": "old"}]})
    new = build_descriptor(spec, {"exports": [{"kind": "function", "name": "new"}]})
    baseline = ContractBaseline(package_version="0.1.0b9", descriptors=(old,))
    _install_state(monkeypatch, policy, (new,), baseline)

    report = service.build_contract_report(
        tmp_path,
        base_ref="pre-adoption",
        mode="snapshot",
    )

    assert report.errors == (
        "snapshot requires historical contract state or explicit initialization",
    )
    assert not report.can_snapshot


def test_missing_baseline_without_initialization_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Ordinary checks never infer initial adoption."""
    spec = _spec()
    policy = ContractPolicy(contracts=(spec,))
    live = build_descriptor(spec, {"exports": [{"kind": "function", "name": "current"}]})
    _install_state(monkeypatch, policy, (live,), None)

    report = service.build_contract_report(tmp_path, base_ref="old", mode="check")

    assert report.errors == ("current contract baseline is missing",)


def test_staged_snapshot_and_materialization_failure_are_typed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Unsupported staged mutation and index failures return invalid reports."""
    snapshot = service.build_contract_report(
        tmp_path,
        base_ref="HEAD",
        mode="snapshot",
        staged=True,
    )

    def unavailable(_root: Path) -> Never:
        raise ContractError("staged state unavailable")

    monkeypatch.setattr(service.index_state, "materialized_contract_index", unavailable)
    check = service.build_contract_report(
        tmp_path,
        base_ref="HEAD",
        mode="check",
        staged=True,
    )

    assert snapshot.errors == ("staged snapshot is unsupported",)
    assert check.errors == ("staged state unavailable",)
