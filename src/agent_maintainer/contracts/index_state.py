"""Materialize index-authoritative contract inputs into a controlled root."""

from __future__ import annotations

import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from agent_maintainer.contracts.git_base import (
    BASELINE_PATH,
    POLICY_PATH,
    read_index_text,
)
from agent_maintainer.contracts.models import (
    ContractError,
    ContractPolicy,
    GitContractError,
    PolicyError,
)
from agent_maintainer.contracts.policy import parse_policy


@contextmanager
def materialized_contract_index(repo_root: Path) -> Generator[Path]:
    """Yield one temporary root containing only staged contract inputs."""

    with tempfile.TemporaryDirectory(prefix="agent-maintainer-contract-index-") as raw:
        destination = Path(raw)
        materialize_contract_index(repo_root, destination)
        yield destination


def materialize_contract_index(repo_root: Path, destination: Path) -> None:
    """Write only staged contract inputs into one controlled temporary root."""

    root = repo_root.resolve()
    policy_text = read_index_text(root, POLICY_PATH)
    if policy_text is None:
        raise GitContractError("staged contract policy is missing")
    policy = _parse_staged_policy(policy_text)
    paths = {
        POLICY_PATH,
        BASELINE_PATH,
        policy.package_version_file,
        *(spec.source for spec in policy.contracts),
    }
    for path in sorted(paths):
        text = policy_text if path == POLICY_PATH else read_index_text(root, path)
        if text is not None:
            _write_materialized(destination, path, text)


def _parse_staged_policy(text: str) -> ContractPolicy:
    try:
        return parse_policy(text, source=f":{POLICY_PATH}")
    except PolicyError as exc:
        raise GitContractError("staged contract policy is invalid") from exc


def _write_materialized(destination: Path, path: str, text: str) -> None:
    candidate = destination / path
    try:
        candidate.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ContractError(f"could not materialize staged contract path: {path}") from exc
    try:
        candidate.write_text(text, encoding="utf-8")
    except OSError as exc:
        raise ContractError(f"could not materialize staged contract path: {path}") from exc
