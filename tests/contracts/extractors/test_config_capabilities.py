"""Configuration-capability contract extraction tests."""

import json
from pathlib import Path
from typing import cast

import pytest

from agent_maintainer.contracts.extractors import config_capabilities
from agent_maintainer.contracts.extractors.config_capabilities import (
    extract_config_capabilities,
)
from agent_maintainer.contracts.models import ContractSpec, ExtractionError


def _spec() -> ContractSpec:
    return ContractSpec(
        id="agent-maintainer-config",
        kind="config-capabilities",
        owner="agent_maintainer.config",
        stability="beta",
        revision=1,
        source="config/capabilities.json",
    )


def _field(name: str, **updates: object) -> dict[str, object]:
    field: dict[str, object] = {
        "cli_override": "none",
        "constraints": {
            "allow_empty": False,
            "choices": ["z", "a"],
            "maximum": 10.0,
            "minimum": 0.0,
            "minimum_exclusive": False,
            "repository_relative_path": False,
            "verification_profiles": False,
        },
        "default": {"enabled": True},
        "description": f"Configure {name}.",
        "environment": f"AGENT_MAINTAINER_{name.upper()}",
        "environment_style": "standard",
        "label": name.replace("_", " ").title(),
        "name": name,
        "stability": "stable",
        "toml_aliases": [f"legacy_{name}"],
        "toml_key": name,
        "value_kind": "mapping",
    }
    field.update(updates)
    return field


def _document(fields: list[dict[str, object]]) -> dict[str, object]:
    return {
        "fields": fields,
        "nested_environment": {"java.enabled": "AGENT_MAINTAINER_JAVA_ENABLED"},
        "nested_tables": {"java": ["enabled", "gradle_command"]},
        "precedence": ["defaults", "file", "environment"],
        "runtime_environment": ["AGENT_MAINTAINER_RUNTIME"],
        "schema_version": 1,
    }


def _write(tmp_path: Path, document: object) -> None:
    path = tmp_path / "config/capabilities.json"
    path.parent.mkdir()
    path.write_text(json.dumps(document), encoding="utf-8")


def test_config_fields_are_sorted_and_normalized(tmp_path: Path) -> None:
    """Capability members retain only exact semantic contract facts."""
    _write(tmp_path, _document([_field("z_field"), _field("a_field")]))

    descriptor = extract_config_capabilities(tmp_path, _spec())

    members = cast(list[dict[str, object]], descriptor.body["fields"])
    assert [member["name"] for member in members] == ["a_field", "z_field"]
    assert members[0] == {
        "aliases": ["legacy_a_field"],
        "choices": ["a", "z"],
        "constraints": {
            "allow_empty": False,
            "maximum": 10.0,
            "minimum": 0.0,
            "minimum_exclusive": False,
            "repository_relative_path": False,
            "verification_profiles": False,
        },
        "default": {"enabled": True},
        "environment": ["AGENT_MAINTAINER_A_FIELD"],
        "kind": "mapping",
        "name": "a_field",
        "required": False,
        "stability": "stable",
    }


def test_config_nested_field_without_environment_normalizes_empty(tmp_path: Path) -> None:
    """Nested-table fields may intentionally have no direct environment variable."""
    _write(
        tmp_path,
        _document([_field("java", environment=None, environment_style=None)]),
    )

    descriptor = extract_config_capabilities(tmp_path, _spec())
    members = cast(list[dict[str, object]], descriptor.body["fields"])

    assert members[0]["environment"] == []


@pytest.mark.parametrize(
    ("fields", "message"),
    (
        ([_field("same"), _field("same")], "duplicate field"),
        ([_field("bad\nname")], "safe text"),
        ([_field("bad", stability="experimental")], "stability"),
        ([_field("bad", unknown=True)], "unknown field key"),
    ),
)
def test_config_rejects_ambiguous_or_unknown_fields(
    tmp_path: Path,
    fields: list[dict[str, object]],
    message: str,
) -> None:
    """Authored capability ambiguity fails closed."""
    _write(tmp_path, _document(fields))

    with pytest.raises(ExtractionError, match=message):
        extract_config_capabilities(tmp_path, _spec())


def test_config_rejects_non_finite_numbers(tmp_path: Path) -> None:
    """Defaults and constraints remain canonical JSON values."""
    _write(tmp_path, _document([_field("bad", default=float("nan"))]))

    with pytest.raises(ExtractionError, match="finite"):
        extract_config_capabilities(tmp_path, _spec())


def test_config_enforces_member_limit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Capability input cannot exceed the shared member bound."""
    monkeypatch.setattr(config_capabilities, "MAX_MEMBERS", 1)
    _write(tmp_path, _document([_field("a"), _field("b")]))

    with pytest.raises(ExtractionError, match="bounded"):
        extract_config_capabilities(tmp_path, _spec())
