"""Contract extractor routing and aggregate behavior tests."""

from pathlib import Path
from typing import cast

import pytest

from agent_maintainer.contracts import extraction
from agent_maintainer.contracts.models import (
    ContractKind,
    ContractPolicy,
    ContractSpec,
    Descriptor,
    ExtractionError,
)


def _spec(contract_id: str, kind: ContractKind = "config-capabilities") -> ContractSpec:
    return ContractSpec(
        id=contract_id,
        kind=kind,
        owner="agent_maintainer.config",
        stability="beta",
        revision=1,
        source=f"config/{contract_id}.json",
    )


def _descriptor(spec: ContractSpec) -> Descriptor:
    return extraction.build_descriptor(spec, {"members": []})


def test_extract_all_is_sorted_by_contract_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Aggregate extraction has deterministic routing and descriptor order."""
    observed: list[str] = []

    def fake_extract(_root: Path, spec: ContractSpec) -> Descriptor:
        observed.append(spec.id)
        return _descriptor(spec)

    monkeypatch.setattr(extraction, "extract_contract", fake_extract)
    policy = ContractPolicy(contracts=(_spec("z-contract"), _spec("a-contract")))

    descriptors = extraction.extract_all(tmp_path, policy)

    assert tuple(item.contract_id for item in descriptors) == ("a-contract", "z-contract")
    assert observed == ["a-contract", "z-contract"]


def test_unknown_kind_cannot_reach_routing(tmp_path: Path) -> None:
    """Runtime-invalid kinds fail closed even if a caller bypasses static typing."""
    spec = _spec("unsafe", cast(ContractKind, "runtime-reflection"))

    with pytest.raises(ExtractionError, match=r"unsafe.*unsupported kind"):
        extraction.extract_contract(tmp_path, spec)


def test_extractor_failure_is_bounded_to_contract_and_source(tmp_path: Path) -> None:
    """Failures identify the normalized contract without exposing absolute roots."""
    spec = _spec("missing-config")

    with pytest.raises(ExtractionError) as raised:
        extraction.extract_contract(tmp_path, spec)

    message = str(raised.value)
    assert "missing-config" in message
    assert "config/missing-config.json" in message
    assert str(tmp_path) not in message


def test_extract_all_stops_without_returning_partial_data(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """One failed contract aborts aggregate extraction before later adapters run."""
    observed: list[str] = []

    def fake_extract(_root: Path, spec: ContractSpec) -> Descriptor:
        observed.append(spec.id)
        if spec.id == "b-contract":
            raise ExtractionError("b-contract failed")
        return _descriptor(spec)

    monkeypatch.setattr(extraction, "extract_contract", fake_extract)
    policy = ContractPolicy(
        contracts=(_spec("c-contract"), _spec("b-contract"), _spec("a-contract")),
    )

    with pytest.raises(ExtractionError, match="b-contract"):
        extraction.extract_all(tmp_path, policy)

    assert observed == ["a-contract", "b-contract"]
