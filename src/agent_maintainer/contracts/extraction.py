"""Pure-data contract extractor protocol and deterministic routing."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from agent_maintainer.contracts.extractors.cli_manifest import extract_cli_manifest
from agent_maintainer.contracts.extractors.config_capabilities import (
    extract_config_capabilities,
)
from agent_maintainer.contracts.extractors.json_schema import extract_json_schema
from agent_maintainer.contracts.extractors.python_api import extract_python_api
from agent_maintainer.contracts.models import (
    ContractError,
    ContractPolicy,
    ContractSpec,
    Descriptor,
    ExtractionError,
)
from agent_maintainer.contracts.normalization import build_descriptor as _build_descriptor

Extractor = Callable[[Path, ContractSpec], Descriptor]


def build_descriptor(spec: ContractSpec, body: dict[str, object]) -> Descriptor:
    """Build one normalized descriptor through the public extraction facade."""

    return _build_descriptor(spec, body)


def extract_contract(repo_root: Path, spec: ContractSpec) -> Descriptor:
    """Route one supported contract kind to its pure-data extractor."""

    extractors: dict[str, Extractor] = {
        "cli-manifest": extract_cli_manifest,
        "config-capabilities": extract_config_capabilities,
        "json-schema": extract_json_schema,
        "python-api": extract_python_api,
    }
    extractor = extractors.get(spec.kind)
    if extractor is None:
        raise ExtractionError(f"{spec.id} uses unsupported kind: {spec.kind}")
    try:
        return extractor(repo_root, spec)
    except ContractError as exc:
        raise ExtractionError(f"{spec.id} ({spec.source}): {exc}") from exc


def extract_all(repo_root: Path, policy: ContractPolicy) -> tuple[Descriptor, ...]:
    """Extract every configured contract in deterministic identity order."""

    return tuple(
        extract_contract(repo_root, spec)
        for spec in sorted(policy.contracts, key=lambda item: item.id)
    )
