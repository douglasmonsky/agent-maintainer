"""Pure-data contract extractor protocol and deterministic routing."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from agent_maintainer.contracts.models import (
    ContractError,
    ContractPolicy,
    ContractSpec,
    Descriptor,
    ExtractionError,
)
from agent_maintainer.contracts.normalization import build_descriptor

__all__ = ["Extractor", "build_descriptor", "extract_all", "extract_contract"]


class Extractor(Protocol):
    """One repository-confined semantic contract adapter."""

    def extract(self, repo_root: Path, spec: ContractSpec) -> Descriptor:
        """Extract one normalized descriptor without executing target code."""

        ...


def extract_contract(repo_root: Path, spec: ContractSpec) -> Descriptor:
    """Route one supported contract kind to its pure-data extractor."""

    from agent_maintainer.contracts.extractors.cli_manifest import extract_cli_manifest
    from agent_maintainer.contracts.extractors.config_capabilities import (
        extract_config_capabilities,
    )
    from agent_maintainer.contracts.extractors.python_api import extract_python_api

    extractors = {
        "cli-manifest": extract_cli_manifest,
        "config-capabilities": extract_config_capabilities,
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
