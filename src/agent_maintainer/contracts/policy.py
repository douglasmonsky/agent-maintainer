"""Strict TOML decoding for repository-owned contract policy."""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from agent_maintainer.contracts.models import (
    Classification,
    ContractDecision,
    ContractKind,
    ContractPolicy,
    ContractSpec,
    PolicyError,
    VersionImpact,
)
from agent_maintainer.contracts.paths import read_confined_text
from agent_maintainer.core.repo_paths import RepoPathError, validate_repo_path

DEFAULT_POLICY_PATH = Path(".agent-maintainer/contracts.toml")
IDENTIFIER = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
OWNER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")
FINGERPRINT = re.compile(r"^sha256:[0-9a-f]{64}$")
KINDS = frozenset(("config-capabilities", "cli-manifest", "python-api", "json-schema"))
CLASSIFICATIONS = frozenset(("breaking", "compatible"))
STABILITIES = frozenset(("beta", "stable"))
IMPACTS = frozenset(("prerelease", "patch", "minor", "major"))
FIRST_SAFE_CODEPOINT = ord(" ")
TOP_KEYS = frozenset(
    (
        "contracts",
        "decisions",
        "package_version_file",
        "pre_one_breaking",
        "stable_breaking",
        "version",
    )
)
CONTRACT_KEYS = frozenset(
    (
        "exports",
        "id",
        "kind",
        "migration_paths",
        "owner",
        "revision",
        "source",
        "stability",
    )
)
DECISION_KEYS = frozenset(("classification", "contract", "fingerprint", "reason"))


def load_policy(
    repo_root: Path,
    path: Path = DEFAULT_POLICY_PATH,
) -> ContractPolicy | None:
    """Load strict authored policy, or return None when it is absent."""

    candidate = repo_root / path
    if not candidate.exists() and not candidate.is_symlink():
        return None
    try:
        text = read_confined_text(repo_root, path.as_posix(), label="contract policy")
    except ValueError as exc:
        raise PolicyError(str(exc)) from exc
    return parse_policy(text, source=path.as_posix())


def parse_policy(text: str, *, source: str) -> ContractPolicy:
    """Decode one strict policy document from bounded UTF-8 text."""

    try:
        raw = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise PolicyError(f"invalid contract policy {source}") from exc
    _reject_unknown(raw, TOP_KEYS, label="top-level")
    if raw.get("version") != 1 or isinstance(raw.get("version"), bool):
        raise PolicyError("policy version must be exactly 1")
    contracts = tuple(
        _decode_contract(item, index)
        for index, item in enumerate(_tables(raw.get("contracts", []), "contracts"))
    )
    decisions = tuple(
        _decode_decision(item, index)
        for index, item in enumerate(_tables(raw.get("decisions", []), "decisions"))
    )
    _reject_duplicates(tuple(item.id for item in contracts), "contract id")
    _reject_duplicates(
        tuple((item.contract, item.fingerprint) for item in decisions),
        "decision fingerprint",
    )
    contract_ids = frozenset(item.id for item in contracts)
    unknown_decision = next(
        (item.contract for item in decisions if item.contract not in contract_ids),
        None,
    )
    if unknown_decision is not None:
        raise PolicyError(f"decision references unknown contract: {unknown_decision}")
    return ContractPolicy(
        package_version_file=_path(raw.get("package_version_file"), "package_version_file"),
        pre_one_breaking=_impact(raw.get("pre_one_breaking"), "pre_one_breaking"),
        stable_breaking=_impact(raw.get("stable_breaking"), "stable_breaking"),
        contracts=tuple(sorted(contracts, key=lambda item: item.id)),
        decisions=tuple(sorted(decisions, key=lambda item: (item.contract, item.fingerprint))),
    )


def _decode_contract(value: object, index: int) -> ContractSpec:
    raw = _table(value, f"contracts[{index}]")
    _reject_unknown(raw, CONTRACT_KEYS, label="contract")
    kind = _kind(raw.get("kind"), f"contracts[{index}].kind")
    exports = _text_tuple(raw.get("exports", []), f"contracts[{index}].exports")
    if exports and kind != "python-api":
        raise PolicyError(f"contracts[{index}].exports is valid only for python-api")
    return ContractSpec(
        id=_identifier(raw.get("id"), f"contracts[{index}].id"),
        kind=kind,
        owner=_owner(raw.get("owner"), f"contracts[{index}].owner"),
        stability=_stability(raw.get("stability"), f"contracts[{index}].stability"),
        revision=_revision(raw.get("revision"), f"contracts[{index}].revision"),
        source=_path(raw.get("source"), f"contracts[{index}].source"),
        exports=exports,
        migration_paths=_path_tuple(
            raw.get("migration_paths", []),
            f"contracts[{index}].migration_paths",
        ),
    )


def _decode_decision(value: object, index: int) -> ContractDecision:
    raw = _table(value, f"decisions[{index}]")
    _reject_unknown(raw, DECISION_KEYS, label="decision")
    fingerprint_value = raw.get("fingerprint")
    if not isinstance(fingerprint_value, str) or not FINGERPRINT.fullmatch(fingerprint_value):
        raise PolicyError(f"decisions[{index}].fingerprint must be an exact SHA-256")
    classification_value = raw.get("classification")
    if not isinstance(classification_value, str) or classification_value not in CLASSIFICATIONS:
        raise PolicyError(f"decisions[{index}].classification must be breaking or compatible")
    return ContractDecision(
        contract=_identifier(raw.get("contract"), f"decisions[{index}].contract"),
        fingerprint=fingerprint_value,
        classification=cast(Classification, classification_value),
        reason=_nonempty_text(raw.get("reason"), f"decisions[{index}].reason"),
    )


def _table(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise PolicyError(f"{label} must be a table")
    return cast(Mapping[str, object], value)


def _tables(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise PolicyError(f"{label} must be an array of tables")
    return cast(list[object], value)


def _reject_unknown(raw: Mapping[str, object], allowed: frozenset[str], *, label: str) -> None:
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise PolicyError(f"unknown {label} key: {unknown[0]}")


def _identifier(value: object, label: str) -> str:
    text = _nonempty_text(value, label)
    if not IDENTIFIER.fullmatch(text):
        raise PolicyError(f"{label} must be a kebab-case identifier")
    return text


def _owner(value: object, label: str) -> str:
    text = _nonempty_text(value, label)
    if not OWNER.fullmatch(text):
        raise PolicyError(f"{label} must be a dotted owner name")
    return text


def _kind(value: object, label: str) -> ContractKind:
    if not isinstance(value, str) or value not in KINDS:
        raise PolicyError(f"{label} contains unsupported kind")
    return value


def _impact(value: object, label: str) -> VersionImpact:
    if not isinstance(value, str) or value not in IMPACTS:
        raise PolicyError(f"{label} contains unsupported version impact")
    return cast(VersionImpact, value)


def _stability(value: object, label: str) -> str:
    if not isinstance(value, str) or value not in STABILITIES:
        raise PolicyError(f"{label} must be beta or stable")
    return value


def _revision(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise PolicyError(f"{label} must be a positive integer")
    return value


def _path(value: object, label: str) -> str:
    text = _nonempty_text(value, label)
    try:
        return validate_repo_path(text, label=label)
    except RepoPathError as exc:
        raise PolicyError(str(exc)) from exc


def _path_tuple(value: object, label: str) -> tuple[str, ...]:
    return tuple(_path(item, label) for item in _text_list(value, label))


def _text_tuple(value: object, label: str) -> tuple[str, ...]:
    return tuple(_nonempty_text(item, label) for item in _text_list(value, label))


def _text_list(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise PolicyError(f"{label} must be an array of text")
    values = cast(list[object], value)
    if not all(isinstance(item, str) for item in values):
        raise PolicyError(f"{label} must be an array of text")
    _reject_duplicates(tuple(values), label)
    return values


def _nonempty_text(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or any(ord(character) < FIRST_SAFE_CODEPOINT for character in value)
    ):
        raise PolicyError(f"{label} must be non-empty safe text")
    return value


def _reject_duplicates(values: tuple[object, ...], label: str) -> None:
    seen: set[object] = set()
    for value in values:
        if value in seen:
            raise PolicyError(f"duplicate {label}: {value}")
        seen.add(value)
