"""Tests for immutable contract-ratchet domain models."""

from dataclasses import FrozenInstanceError

import pytest

from agent_maintainer.contracts import limits
from agent_maintainer.contracts.models import (
    ContractChange,
    ContractObligation,
    ContractReport,
    Descriptor,
)

EXPECTED_LIMITS = (1_000_000, 256, 10_000, 64, 200)


def test_descriptor_is_immutable_and_semantic_only() -> None:
    """Descriptors reject mutation and contain repository-relative facts."""
    descriptor = Descriptor(
        contract_id="docsync-api",
        kind="python-api",
        owner="docsync.api",
        stability="beta",
        revision=1,
        sources=("src/docsync/api.py",),
        body={"exports": []},
        fingerprint="sha256:abc",
    )

    with pytest.raises(FrozenInstanceError):
        descriptor.revision = 2  # type: ignore[misc]


def test_change_identity_is_exact_and_bounded() -> None:
    """Change identity uses only normalized contract coordinates."""
    change = ContractChange(
        contract_id="docsync-api",
        operation="member-remove",
        path="exports.check_repo",
        before="function",
        after=None,
        classification="breaking",
        fingerprint="sha256:def",
        reason="export removed",
    )

    assert change.identity() == (
        "docsync-api",
        "member-remove",
        "exports.check_repo",
        "sha256:def",
    )


def test_report_unresolved_tracks_errors_and_obligations() -> None:
    """A report is unresolved for either invalid input or failed obligations."""
    clean = ContractReport(mode="check")
    blocked = ContractReport(
        mode="check",
        obligations=(
            ContractObligation(
                kind="contract-revision",
                contract_id="docsync-api",
                status="unresolved",
                message="revision must advance",
            ),
        ),
    )
    invalid = ContractReport(mode="check", errors=("invalid policy",))

    assert clean.unresolved is False
    assert blocked.unresolved is True
    assert invalid.unresolved is True


def test_security_limits_are_explicit_and_finite() -> None:
    """All extraction and reporting budgets stay fixed and bounded."""
    assert (
        limits.MAX_INPUT_BYTES,
        limits.MAX_CONTRACTS,
        limits.MAX_MEMBERS,
        limits.MAX_DEPTH,
        limits.MAX_REPORT_ITEMS,
    ) == EXPECTED_LIMITS
