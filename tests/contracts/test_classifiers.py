"""Kind-aware semantic compatibility classification tests."""

from __future__ import annotations

import pytest

from agent_maintainer.contracts.classifiers import classify_change
from agent_maintainer.contracts.models import Classification, ContractKind


@pytest.mark.parametrize(
    ("before", "after", "classification"),
    (
        ({"required": False}, {"required": True}, "breaking"),
        ({"types": ["string"]}, {"types": ["null", "string"]}, "compatible"),
        ({"enum": ["a"]}, {"enum": ["a", "b"]}, "review-required"),
        ({"additional_properties": True}, {"additional_properties": False}, "breaking"),
        ({}, {"additional_properties": False}, "breaking"),
        ({"min_length": 2}, {"min_length": 3}, "breaking"),
        ({"maximum": 10}, {"maximum": 12}, "compatible"),
    ),
)
def test_schema_property_change_matrix(
    before: dict[str, object],
    after: dict[str, object],
    classification: Classification,
) -> None:
    """Schema leaves distinguish narrowing, widening, and ambiguous enum growth."""
    key = next(iter(before or after))
    actual, _reason = classify_change(
        "json-schema",
        _operation(key),
        f"/properties/value/{key}",
        before.get(key),
        after[key],
    )

    assert actual == classification


@pytest.mark.parametrize(
    ("kind", "path", "after", "classification"),
    (
        ("config-capabilities", "/fields/new", {"required": False, "default": 1}, "compatible"),
        ("config-capabilities", "/fields/new", {"required": True}, "breaking"),
        ("cli-manifest", "/commands/verify", {"path": ["verify"]}, "compatible"),
        ("cli-manifest", "/commands/verify/options/new", {"required": False}, "compatible"),
        ("cli-manifest", "/commands/verify/options/new", {"required": True}, "breaking"),
        ("python-api", "/exports/new", {"name": "new"}, "compatible"),
        ("python-api", "/exports/run/parameters/limit", {"has_default": True}, "compatible"),
        ("python-api", "/exports/run/parameters/limit", {"has_default": False}, "breaking"),
        ("json-schema", "/properties/new", {"required": False}, "compatible"),
        ("json-schema", "/properties/new", {"required": True}, "breaking"),
    ),
)
def test_member_addition_matrix(
    kind: ContractKind,
    path: str,
    after: dict[str, object],
    classification: Classification,
) -> None:
    """Additions are classified using their contract-specific call-site obligations."""
    actual, _reason = classify_change(kind, "member-add", path, None, after)

    assert actual == classification


@pytest.mark.parametrize(
    ("operation", "before", "after", "classification"),
    (
        ("member-remove", {"name": "old"}, None, "breaking"),
        ("alias-change", [], ["legacy"], "compatible"),
        ("alias-change", ["legacy"], [], "breaking"),
        ("member-rename", {"name": "old"}, {"name": "new"}, "review-required"),
        (
            "member-rename",
            {"name": "old"},
            {"aliases": ["old"], "name": "new"},
            "compatible",
        ),
        ("unsupported-semantic-change", [], ["/oneOf"], "review-required"),
    ),
)
def test_identity_and_ambiguity_matrix(
    operation: str,
    before: object | None,
    after: object | None,
    classification: Classification,
) -> None:
    """Removal, aliases, renames, and unproved semantics retain explicit defaults."""
    actual, _reason = classify_change(
        "json-schema",
        operation,
        "/properties/value",
        before,
        after,
    )

    assert actual == classification


@pytest.mark.parametrize(
    ("kind", "path", "before", "after", "classification"),
    (
        ("config-capabilities", "/fields/value/default", 1, 2, "breaking"),
        ("cli-manifest", "/commands/check/options/base/required", False, True, "breaking"),
        ("python-api", "/exports/run/parameters/order", ["a", "b"], ["b", "a"], "breaking"),
        ("json-schema", "/properties/value/types", ["string"], ["integer"], "breaking"),
    ),
)
def test_cross_kind_breaking_defaults(
    kind: ContractKind,
    path: str,
    before: object,
    after: object,
    classification: Classification,
) -> None:
    """Known incompatible changes default to breaking across extractor families."""
    actual, _reason = classify_change(
        kind,
        _operation(path.rsplit("/", 1)[-1]),
        path,
        before,
        after,
    )

    assert actual == classification


def _operation(key: str) -> str:
    if key in {"types", "kind", "annotation", "return_annotation"}:
        return "type-change"
    if key == "required":
        return "requiredness-change"
    if key in {"default", "has_default"}:
        return "default-change"
    if key == "aliases":
        return "alias-change"
    if key == "unsupported_semantics":
        return "unsupported-semantic-change"
    return "constraint-change"
