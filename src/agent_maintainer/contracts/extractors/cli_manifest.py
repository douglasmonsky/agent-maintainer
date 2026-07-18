"""Strict CLI-manifest semantic contract extraction."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from agent_maintainer.contracts.models import ContractSpec, Descriptor, ExtractionError
from agent_maintainer.contracts.normalization import (
    build_descriptor,
    exact_keys,
    load_json_object,
    object_array,
    safe_text,
    sorted_json_scalars,
    text_array,
    validate_json_value,
)

NAME_KEY = "name"
DOCUMENT_KEYS = frozenset(("commands", "console_scripts", "schema_version"))
COMMAND_KEYS = frozenset(("arguments", "exit_statuses", "options", "path"))
OPTION_KEYS = frozenset(
    (
        "aliases",
        "choices",
        "default",
        "environment",
        "kind",
        "multiple",
        NAME_KEY,
        "required",
        "stability",
    )
)
ARGUMENT_KEYS = frozenset(
    ("choices", "default", "kind", "multiple", NAME_KEY, "required", "stability")
)
REQUIRED_OPTION_KEYS = frozenset(("aliases", "default", "kind", "multiple", NAME_KEY, "required"))
REQUIRED_ARGUMENT_KEYS = frozenset(("kind", "multiple", NAME_KEY, "required"))
STABILITIES = frozenset(("beta", "stable"))
MAX_EXIT_STATUS = 255


def extract_cli_manifest(repo_root: Path, spec: ContractSpec) -> Descriptor:
    """Extract console scripts, commands, options, arguments, and exits."""

    if spec.kind != "cli-manifest":
        raise ExtractionError("CLI extractor requires cli-manifest kind")
    document = load_json_object(repo_root, spec)
    exact_keys(document, DOCUMENT_KEYS, label="manifest")
    if document.get("schema_version") != 1 or isinstance(document.get("schema_version"), bool):
        raise ExtractionError("manifest schema_version must be exactly 1")
    scripts = sorted(text_array(document.get("console_scripts"), label="console script"))
    command_values = object_array(document.get("commands"), label="commands")
    commands = [_normalize_command(item, spec) for item in command_values]
    identities = [_command_identity(command) for command in commands]
    if len(identities) != len(set(identities)):
        raise ExtractionError("duplicate command identity")
    commands.sort(key=_command_identity)
    return build_descriptor(spec, {"commands": commands, "console_scripts": scripts})


def _normalize_command(raw: dict[str, object], spec: ContractSpec) -> dict[str, object]:
    exact_keys(
        raw,
        COMMAND_KEYS,
        label="command",
        required=frozenset(("exit_statuses", "options", "path")),
    )
    path = text_array(raw.get("path"), label="command path", allow_empty=False)
    option_values = object_array(raw.get("options"), label="options")
    options = [_normalize_option(item, spec) for item in option_values]
    arguments = [
        _normalize_argument(item, spec)
        for item in object_array(raw.get("arguments", []), label="arguments")
    ]
    _reject_duplicate_members(options, "option")
    _reject_duplicate_members(arguments, "argument")
    options.sort(key=lambda item: str(item[NAME_KEY]))
    arguments.sort(key=lambda item: str(item[NAME_KEY]))
    return {
        "arguments": arguments,
        "exit_statuses": _exit_statuses(raw.get("exit_statuses")),
        "options": options,
        "path": path,
    }


def _normalize_option(raw: dict[str, object], spec: ContractSpec) -> dict[str, object]:
    exact_keys(raw, OPTION_KEYS, label="option", required=REQUIRED_OPTION_KEYS)
    aliases = sorted(text_array(raw.get("aliases"), label="option alias"))
    environment_value = raw.get("environment")
    environment = (
        []
        if environment_value is None
        else [safe_text(environment_value, label="option environment")]
    )
    return _normalize_member(raw, spec, aliases=aliases, environment=environment)


def _normalize_argument(raw: dict[str, object], spec: ContractSpec) -> dict[str, object]:
    exact_keys(raw, ARGUMENT_KEYS, label="argument", required=REQUIRED_ARGUMENT_KEYS)
    return _normalize_member(raw, spec, aliases=[], environment=[])


def _normalize_member(
    raw: dict[str, object],
    spec: ContractSpec,
    *,
    aliases: list[str],
    environment: list[str],
) -> dict[str, object]:
    required = raw.get("required")
    multiple = raw.get("multiple")
    if not isinstance(required, bool) or not isinstance(multiple, bool):
        raise ExtractionError("CLI required and multiple values must be boolean")
    default = raw.get("default")
    validate_json_value(default)
    stability = safe_text(raw.get("stability", spec.stability), label="CLI stability")
    if stability not in STABILITIES:
        raise ExtractionError("CLI stability must be beta or stable")
    return {
        "aliases": aliases,
        "choices": sorted_json_scalars(raw.get("choices", []), label="CLI choices"),
        "constraints": {"multiple": multiple},
        "default": default,
        "environment": environment,
        "kind": safe_text(raw.get("kind"), label="CLI kind"),
        NAME_KEY: safe_text(raw.get(NAME_KEY), label="CLI name"),
        "required": required,
        "stability": stability,
    }


def _exit_statuses(value: object) -> list[int]:
    if not isinstance(value, list):
        raise ExtractionError("exit statuses must be an array")
    statuses: list[int] = []
    for item in cast(list[object], value):
        if not isinstance(item, int) or isinstance(item, bool) or not 0 <= item <= MAX_EXIT_STATUS:
            raise ExtractionError("exit status must be between 0 and 255")
        statuses.append(item)
    if len(statuses) != len(set(statuses)):
        raise ExtractionError("duplicate exit status")
    return sorted(statuses)


def _command_identity(command: dict[str, object]) -> tuple[str, ...]:
    path = command.get("path")
    if not isinstance(path, list):
        raise ExtractionError("normalized command path must be an array")
    return tuple(safe_text(item, label="command path") for item in cast(list[object], path))


def _reject_duplicate_members(members: list[dict[str, object]], label: str) -> None:
    identities = [str(member[NAME_KEY]) for member in members]
    if len(identities) != len(set(identities)):
        raise ExtractionError(f"duplicate {label} identity")
