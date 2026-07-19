"""CLI-manifest contract extraction tests."""

import json
from pathlib import Path
from typing import cast

import pytest

from agent_maintainer.contracts.comparison import compare_descriptors
from agent_maintainer.contracts.extractors.cli_manifest import extract_cli_manifest
from agent_maintainer.contracts.models import ContractSpec, ExtractionError


def _spec() -> ContractSpec:
    return ContractSpec(
        id="agent-maintainer-cli",
        kind="cli-manifest",
        owner="agent_maintainer.cli",
        stability="beta",
        revision=1,
        source="config/cli.json",
    )


def _write(tmp_path: Path, document: object) -> None:
    path = tmp_path / "config/cli.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8")


def _option(name: str, **updates: object) -> dict[str, object]:
    option: dict[str, object] = {
        "aliases": ["-b"],
        "choices": ["z", "a"],
        "default": "origin/main",
        "environment": "AGENT_MAINTAINER_BASE_REF",
        "kind": "string",
        "multiple": False,
        "name": name,
        "required": False,
        "stability": "beta",
    }
    option.update(updates)
    return option


def _command(path: list[str], **updates: object) -> dict[str, object]:
    command: dict[str, object] = {
        "arguments": [
            {
                "choices": [],
                "default": None,
                "kind": "path",
                "multiple": False,
                "name": "target",
                "required": True,
                "stability": "beta",
            }
        ],
        "exit_statuses": [2, 0, 1],
        "options": [_option("base-ref")],
        "path": path,
    }
    command.update(updates)
    return command


def _document(commands: list[dict[str, object]]) -> dict[str, object]:
    return {
        "commands": commands,
        "console_scripts": ["maintain", "agent-maintainer"],
        "schema_version": 1,
    }


def test_cli_options_arguments_and_commands_are_normalized(tmp_path: Path) -> None:
    """CLI members have stable identities, aliases, multiplicity, and exits."""
    _write(
        tmp_path,
        _document([_command(["verify"]), _command(["contract", "check"])]),
    )

    descriptor = extract_cli_manifest(tmp_path, _spec())

    assert descriptor.body["console_scripts"] == ["agent-maintainer", "maintain"]
    commands = cast(list[dict[str, object]], descriptor.body["commands"])
    assert [command["path"] for command in commands] == [
        ["contract", "check"],
        ["verify"],
    ]
    assert commands[0]["exit_statuses"] == [0, 1, 2]
    options = cast(list[dict[str, object]], commands[0]["options"])
    arguments = cast(list[dict[str, object]], commands[0]["arguments"])
    assert options[0] == {
        "aliases": ["-b"],
        "choices": ["a", "z"],
        "constraints": {"multiple": False},
        "default": "origin/main",
        "environment": ["AGENT_MAINTAINER_BASE_REF"],
        "kind": "string",
        "name": "base-ref",
        "required": False,
        "stability": "beta",
    }
    assert arguments[0]["name"] == "target"
    assert arguments[0]["aliases"] == []


def test_cli_positional_argument_reordering_is_breaking(tmp_path: Path) -> None:
    """Authored positional order survives extraction and reaches comparison."""
    prototype = cast(list[dict[str, object]], _command(["copy"])["arguments"])[0]
    source = {**prototype, "name": "source"}
    destination = {**prototype, "name": "destination"}
    _write(tmp_path, _document([_command(["copy"], arguments=[source, destination])]))
    before = extract_cli_manifest(tmp_path, _spec())
    _write(tmp_path, _document([_command(["copy"], arguments=[destination, source])]))
    after = extract_cli_manifest(tmp_path, _spec())

    changes = compare_descriptors((before,), (after,), ())

    assert len(changes) == 1
    assert changes[0].path.endswith("/arguments/order")
    assert changes[0].classification == "breaking"


@pytest.mark.parametrize(
    ("commands", "message"),
    (
        ([_command(["verify"]), _command(["verify"])], "duplicate command"),
        (
            [_command(["verify"], options=[_option("base-ref"), _option("base-ref")])],
            "duplicate option",
        ),
        ([_command(["verify"], unknown=True)], "unknown command key"),
        ([_command(["bad\npath"])], "safe text"),
        ([_command(["verify"], exit_statuses=[0, 256])], "exit status"),
    ),
)
def test_cli_rejects_ambiguous_or_unknown_members(
    tmp_path: Path,
    commands: list[dict[str, object]],
    message: str,
) -> None:
    """CLI identities and bounded scalar facts fail closed on ambiguity."""
    _write(tmp_path, _document(commands))

    with pytest.raises(ExtractionError, match=message):
        extract_cli_manifest(tmp_path, _spec())


def test_cli_rejects_unknown_top_level_key(tmp_path: Path) -> None:
    """The CLI manifest schema is exact and versioned."""
    document = _document([_command(["verify"])])
    document["unknown"] = True
    _write(tmp_path, document)

    with pytest.raises(ExtractionError, match="unknown manifest key"):
        extract_cli_manifest(tmp_path, _spec())
