"""Kind-specific compatibility rules for newly added contract members."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from agent_maintainer.contracts.models import Classification, ContractKind

ClassificationResult = tuple[Classification, str]
MemberRule = Callable[[str, Mapping[str, object]], ClassificationResult]


def classify_member_add(
    kind: ContractKind,
    path: str,
    member: Mapping[str, object],
) -> ClassificationResult:
    """Classify a new member through its contract-kind rule."""

    handlers: dict[ContractKind, MemberRule] = {
        "cli-manifest": _classify_cli_member_add,
        "config-capabilities": _classify_config_member_add,
        "json-schema": _classify_schema_member_add,
        "python-api": _classify_python_member_add,
    }
    handler = handlers.get(kind, _classify_unknown_member_add)
    return handler(path, member)


def _classify_config_member_add(
    _path: str,
    member: Mapping[str, object],
) -> ClassificationResult:
    if member.get("required") is True:
        return "breaking", "new required configuration field"
    if "default" in member:
        return "compatible", "new optional configuration field with default"
    return "review-required", "new optional configuration field has no explicit default"


def _classify_cli_member_add(
    path: str,
    member: Mapping[str, object],
) -> ClassificationResult:
    if "/options/" not in path and "/arguments/" not in path:
        return "compatible", "new command surface"
    if member.get("required") is True:
        return "breaking", "new required command input"
    return "compatible", "new optional command input"


def _classify_python_member_add(
    path: str,
    member: Mapping[str, object],
) -> ClassificationResult:
    if "/parameters/" not in path:
        return "compatible", "new nominated Python API member"
    parameter_kind = member.get("kind")
    optional = member.get("has_default") is True or parameter_kind in {
        "var-keyword",
        "var-positional",
    }
    if optional:
        return "compatible", "new optional Python parameter"
    return "breaking", "new required Python parameter"


def _classify_schema_member_add(
    _path: str,
    member: Mapping[str, object],
) -> ClassificationResult:
    if member.get("required") is True:
        return "breaking", "new required schema property"
    return "compatible", "new optional schema property"


def _classify_unknown_member_add(
    _path: str,
    _member: Mapping[str, object],
) -> ClassificationResult:
    return "review-required", "new member requires review"
