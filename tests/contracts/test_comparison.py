"""Deterministic semantic descriptor comparison tests."""

from __future__ import annotations

from agent_maintainer.contracts.comparison import change_fingerprint, compare_descriptors
from agent_maintainer.contracts.models import ContractDecision, ContractKind, Descriptor


def _descriptor(
    body: dict[str, object],
    *,
    contract_id: str = "public-api",
    kind: ContractKind = "json-schema",
) -> Descriptor:
    return Descriptor(
        contract_id=contract_id,
        kind=kind,
        owner="public.api",
        stability="beta",
        revision=1,
        sources=("schema.json",),
        body=body,
        fingerprint="sha256:" + "0" * 64,
    )


def test_change_fingerprint_is_canonical_and_semantic() -> None:
    """Mapping order is irrelevant while semantic before/after facts remain exact."""
    first = change_fingerprint(
        "public-api",
        "constraint-change",
        "/properties/value/constraints",
        {"minimum": 0, "maximum": 10},
        {"minimum": 1, "maximum": 10},
    )
    reordered = change_fingerprint(
        "public-api",
        "constraint-change",
        "/properties/value/constraints",
        {"maximum": 10, "minimum": 0},
        {"maximum": 10, "minimum": 1},
    )
    changed = change_fingerprint(
        "public-api",
        "constraint-change",
        "/properties/value/constraints",
        {"maximum": 10, "minimum": 0},
        {"maximum": 10, "minimum": 2},
    )

    assert first == reordered
    assert first != changed
    assert first.startswith("sha256:")
    assert "*" not in first


def test_compare_emits_sorted_contract_and_member_operations() -> None:
    """Contract and property identity changes become stable high-level operations."""
    base = (
        _descriptor(
            {"properties": {"old": {"required": False, "types": ["string"]}}},
            contract_id="changed",
        ),
        _descriptor({}, contract_id="removed"),
    )
    current = (
        _descriptor(
            {"properties": {"new": {"required": False, "types": ["string"]}}},
            contract_id="changed",
        ),
        _descriptor({}, contract_id="added"),
    )

    changes = compare_descriptors(base, current, ())

    assert [(item.contract_id, item.operation) for item in changes] == [
        ("added", "contract-add"),
        ("changed", "member-rename"),
        ("removed", "contract-remove"),
    ]
    assert changes[1].classification == "review-required"


def test_exact_decision_resolves_only_its_review_required_change() -> None:
    """A decision is scoped to one contract and original semantic fingerprint."""
    base = (
        _descriptor(
            {"properties": {"value": {"enum": ["a"]}}},
            contract_id="first",
        ),
        _descriptor(
            {"properties": {"value": {"enum": ["a"]}}},
            contract_id="second",
        ),
    )
    current = (
        _descriptor(
            {"properties": {"value": {"enum": ["a", "b"]}}},
            contract_id="first",
        ),
        _descriptor(
            {"properties": {"value": {"enum": ["a", "b"]}}},
            contract_id="second",
        ),
    )
    unresolved = compare_descriptors(base, current, ())
    decision = ContractDecision(
        contract="first",
        fingerprint=unresolved[0].fingerprint,
        classification="compatible",
        reason="The beta consumer handles unknown enum members.",
    )

    resolved = compare_descriptors(base, current, (decision,))

    assert resolved[0].contract_id == "first"
    assert resolved[0].classification == "compatible"
    assert resolved[0].reason == decision.reason
    assert resolved[1].contract_id == "second"
    assert resolved[1].classification == "review-required"


def test_decision_cannot_reclassify_an_already_proved_break() -> None:
    """Authored review decisions do not waive deterministic breaking evidence."""
    base = (_descriptor({"properties": {"value": {"required": False}}}),)
    current = (_descriptor({"properties": {"value": {"required": True}}}),)
    breaking = compare_descriptors(base, current, ())[0]
    decision = ContractDecision(
        contract="public-api",
        fingerprint=breaking.fingerprint,
        classification="compatible",
        reason="This must not weaken a proved break.",
    )

    decided = compare_descriptors(base, current, (decision,))

    assert decided[0].classification == "breaking"
    assert decided[0].reason != decision.reason


def test_parameter_reorder_is_one_breaking_order_change() -> None:
    """Python positional order is semantic even when parameter identities persist."""
    base = (
        _descriptor(
            {"exports": [{"name": "run", "parameters": [{"name": "a"}, {"name": "b"}]}]},
            kind="python-api",
        ),
    )
    current = (
        _descriptor(
            {"exports": [{"name": "run", "parameters": [{"name": "b"}, {"name": "a"}]}]},
            kind="python-api",
        ),
    )

    changes = compare_descriptors(base, current, ())

    assert len(changes) == 1
    assert changes[0].operation == "constraint-change"
    assert changes[0].path.endswith("/parameters/order")
    assert changes[0].classification == "breaking"


def test_first_unsupported_payload_digest_is_evidence_enrichment() -> None:
    """Legacy pointer-only baselines can adopt digests without inventing drift."""
    base = (_descriptor({"unsupported_semantics": ["/oneOf"]}),)
    current = (
        _descriptor(
            {"unsupported_semantics": [f"/oneOf#sha256:{'a' * 64}"]},
        ),
    )

    assert compare_descriptors(base, current, ()) == ()


def test_malformed_unsupported_payload_marker_remains_review_required() -> None:
    """Only exact SHA-256 enrichment markers receive legacy equivalence."""
    base = (_descriptor({"unsupported_semantics": ["/oneOf"]}),)
    current = (_descriptor({"unsupported_semantics": ["/oneOf#sha256:short"]}),)

    changes = compare_descriptors(base, current, ())

    assert len(changes) == 1
    assert changes[0].classification == "review-required"


def test_optional_positional_parameter_is_compatible_only_when_trailing() -> None:
    """Insertion before an existing positional parameter changes positional calls."""
    parameter = {"annotation": "int", "has_default": True, "kind": "positional-or-keyword"}
    base = (
        _descriptor(
            {
                "exports": [
                    {
                        "name": "run",
                        "parameters": [
                            {"name": "first", **parameter},
                            {"name": "last", **parameter},
                        ],
                    }
                ]
            },
            kind="python-api",
        ),
    )
    middle = (
        _descriptor(
            {
                "exports": [
                    {
                        "name": "run",
                        "parameters": [
                            {"name": "first", **parameter},
                            {"name": "inserted", **parameter},
                            {"name": "last", **parameter},
                        ],
                    }
                ]
            },
            kind="python-api",
        ),
    )
    trailing = (
        _descriptor(
            {
                "exports": [
                    {
                        "name": "run",
                        "parameters": [
                            {"name": "first", **parameter},
                            {"name": "last", **parameter},
                            {"name": "inserted", **parameter},
                        ],
                    }
                ]
            },
            kind="python-api",
        ),
    )

    middle_changes = compare_descriptors(base, middle, ())
    trailing_changes = compare_descriptors(base, trailing, ())

    assert any(item.path.endswith("/parameters/order") for item in middle_changes)
    assert any(item.classification == "breaking" for item in middle_changes)
    assert [item.classification for item in trailing_changes] == ["compatible"]
