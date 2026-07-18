"""Structural JSON Schema contract extraction tests."""

import json
from pathlib import Path
from typing import cast

import pytest

from agent_maintainer.contracts.comparison import compare_descriptors
from agent_maintainer.contracts.extractors import json_schema
from agent_maintainer.contracts.extractors.json_schema import extract_json_schema
from agent_maintainer.contracts.models import ContractSpec, ExtractionError

ITEM_LIMIT = 5
MIN_LENGTH = 2
MAX_LENGTH = 8


def _spec() -> ContractSpec:
    return ContractSpec(
        id="wait-record",
        kind="json-schema",
        owner="agent_waits.WaitRecord",
        stability="beta",
        revision=1,
        source="schemas/record.json",
    )


def _write(tmp_path: Path, document: object) -> None:
    path = tmp_path / "schemas/record.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8")


def _body(tmp_path: Path, document: object) -> dict[str, object]:
    _write(tmp_path, document)
    return extract_json_schema(tmp_path, _spec()).body


def test_schema_normalizes_required_properties_and_local_ref(tmp_path: Path) -> None:
    """Object properties, nullable types, and local definitions are structural facts."""
    body = _body(
        tmp_path,
        {
            "$defs": {"id": {"minLength": 1, "type": "string"}},
            "$id": "urn:record",
            "additionalProperties": False,
            "properties": {
                "note": {"type": ["string", "null"]},
                "id": {"$ref": "#/$defs/id"},
            },
            "required": ["id"],
            "type": "object",
        },
    )

    properties = cast(dict[str, dict[str, object]], body["properties"])
    assert list(properties) == ["id", "note"]
    assert properties["id"] == {
        "min_length": 1,
        "required": True,
        "types": ["string"],
    }
    assert properties["note"]["required"] is False
    assert properties["note"]["types"] == ["null", "string"]
    assert body["additional_properties"] is False
    assert body["id"] == "urn:record"


def test_schema_normalizes_enum_const_bounds_pattern_and_items(tmp_path: Path) -> None:
    """Supported scalar constraints and array items retain deterministic facts."""
    body = _body(
        tmp_path,
        {
            "items": {
                "enum": ["z", "a"],
                "maxLength": MAX_LENGTH,
                "minLength": MIN_LENGTH,
                "pattern": "^[a-z]+$",
                "type": "string",
            },
            "maxItems": ITEM_LIMIT,
            "minItems": 1,
            "type": "array",
        },
    )

    items = cast(dict[str, object], body["items"])
    assert body["types"] == ["array"]
    assert body["min_items"] == 1
    assert body["max_items"] == ITEM_LIMIT
    assert items["enum"] == ["a", "z"]
    assert items["min_length"] == MIN_LENGTH
    assert items["max_length"] == MAX_LENGTH
    assert items["pattern"] == "^[a-z]+$"


@pytest.mark.parametrize(
    ("keyword", "value", "expected"),
    (
        ("minimum", 0, 0),
        ("maximum", 10.5, 10.5),
        ("exclusiveMinimum", 0, 0),
        ("exclusiveMaximum", 11, 11),
        ("const", False, False),
    ),
)
def test_schema_normalizes_numeric_and_const_values(
    tmp_path: Path,
    keyword: str,
    value: object,
    expected: object,
) -> None:
    """Numeric bounds and const retain exact canonical JSON values."""
    body = _body(tmp_path, {keyword: value, "type": "number"})

    normalized = {
        "exclusiveMaximum": "exclusive_maximum",
        "exclusiveMinimum": "exclusive_minimum",
    }.get(keyword, keyword)
    assert body[normalized] == expected


@pytest.mark.parametrize(
    "schema_type",
    ("array", "boolean", "integer", "null", "number", "object", "string"),
)
def test_schema_supports_each_structural_type(tmp_path: Path, schema_type: str) -> None:
    """Each type in the supported structural subset is retained exactly."""
    body = _body(tmp_path, {"type": schema_type})

    assert body["types"] == [schema_type]


def test_schema_resolves_escaped_local_definition_name(tmp_path: Path) -> None:
    """Local JSON pointers decode RFC 6901 escape sequences."""
    body = _body(
        tmp_path,
        {"$defs": {"path/name": {"type": "string"}}, "$ref": "#/$defs/path~1name"},
    )

    assert body["types"] == ["string"]


def test_schema_composition_emits_review_required_paths(tmp_path: Path) -> None:
    """Known unproved composition is explicit instead of guessed or ignored."""
    body = _body(
        tmp_path,
        {
            "properties": {"value": {"oneOf": [{"type": "string"}, {"type": "integer"}]}},
            "type": "object",
        },
    )

    unsupported = cast(list[str], body["unsupported_semantics"])
    assert len(unsupported) == 1
    assert unsupported[0].startswith("/properties/value/oneOf#sha256:")


def test_unsupported_composition_payload_changes_require_review(tmp_path: Path) -> None:
    """Unsupported semantics retain a digest, not only their JSON pointer."""
    _write(tmp_path, {"oneOf": [{"type": "string"}]})
    before = extract_json_schema(tmp_path, _spec())
    _write(tmp_path, {"oneOf": [{"type": "integer"}]})
    after = extract_json_schema(tmp_path, _spec())

    changes = compare_descriptors((before,), (after,), ())

    assert len(changes) == 1
    assert changes[0].operation == "unsupported-semantic-change"
    assert changes[0].classification == "review-required"


@pytest.mark.parametrize(
    ("document", "message"),
    (
        ({"$ref": "https://example.com/schema.json"}, "unsafe JSON reference"),
        ({"$ref": "../schema.json#/$defs/value"}, "unsafe JSON reference"),
        ({"$ref": "#/$defs/missing", "$defs": {}}, "missing JSON definition"),
        (
            {
                "$defs": {
                    "a": {"$ref": "#/$defs/b"},
                    "b": {"$ref": "#/$defs/a"},
                },
                "$ref": "#/$defs/a",
            },
            "reference cycle",
        ),
        (
            {
                "properties": {"known": {"type": "string"}},
                "required": ["missing"],
                "type": "object",
            },
            "required property",
        ),
        ({"pattern": "[", "type": "string"}, "pattern"),
        ({"pattern": "bad\npattern", "type": "string"}, "safe text"),
        ({"type": "unknown"}, "schema type"),
        ({"unknownKeyword": True}, "unknown schema key"),
    ),
)
def test_schema_rejects_unsafe_or_ambiguous_semantics(
    tmp_path: Path,
    document: dict[str, object],
    message: str,
) -> None:
    """Unsupported references and malformed structural relationships fail closed."""
    _write(tmp_path, document)

    with pytest.raises(ExtractionError, match=message):
        extract_json_schema(tmp_path, _spec())


def test_schema_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    """Duplicate authored keys cannot shadow earlier schema facts."""
    path = tmp_path / "schemas/record.json"
    path.parent.mkdir()
    path.write_text('{"type":"string","type":"number"}', encoding="utf-8")

    with pytest.raises(ExtractionError, match="duplicate JSON key"):
        extract_json_schema(tmp_path, _spec())


def test_schema_rejects_nonfinite_numbers(tmp_path: Path) -> None:
    """Non-finite numeric spellings never enter a structural descriptor."""
    path = tmp_path / "schemas" / "record.json"
    path.parent.mkdir()
    path.write_text('{"minimum": NaN, "type": "number"}', encoding="utf-8")

    with pytest.raises(ExtractionError, match="finite"):
        extract_json_schema(tmp_path, _spec())


def test_schema_enforces_depth_and_property_limits(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Schema recursion and identity-bearing property arrays are bounded."""
    monkeypatch.setattr(json_schema, "MAX_DEPTH", 2)
    _write(tmp_path, {"items": {"items": {"items": {"type": "string"}}}, "type": "array"})
    with pytest.raises(ExtractionError, match="depth"):
        extract_json_schema(tmp_path, _spec())

    monkeypatch.setattr(json_schema, "MAX_DEPTH", 64)
    monkeypatch.setattr(json_schema, "MAX_MEMBERS", 1)
    _write(
        tmp_path,
        {"properties": {"a": {"type": "string"}, "b": {"type": "string"}}, "type": "object"},
    )
    with pytest.raises(ExtractionError, match=r"properties.*bounded"):
        extract_json_schema(tmp_path, _spec())
