"""Strict TOML loading for declarative repository path-risk policy."""

from __future__ import annotations

import re
import tomllib
from collections.abc import Collection, Mapping
from pathlib import Path
from typing import cast

from agent_maintainer.verification_plan.matching import (
    PathPatternError,
    validate_repo_pattern,
)
from agent_maintainer.verification_plan.models import (
    POLICY_SCHEMA_VERSION,
    EvidenceRequirement,
    PathRiskPolicy,
    PathRiskRule,
)

IDENTIFIER = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TOP_LEVEL_KEYS = frozenset(("rules", "version"))
RULE_KEYS = frozenset(
    (
        "checks",
        "description",
        "evidence",
        "id",
        "mode",
        "paths",
        "profiles",
        "review_categories",
    ),
)
EVIDENCE_KEYS = frozenset(("id", "kind", "message", "minimum", "paths"))
VALID_MODES = frozenset(("advisory", "required"))
CHANGED_PATH_KIND = "changed-path"


class PolicyError(ValueError):
    """Raised when path-risk policy is malformed or internally inconsistent."""


# docsync:evidence.start evidence.readme.path_risk_policy
def load_policy(path: Path) -> PathRiskPolicy | None:
    """Load one strict versioned path-risk policy, or None when absent."""
    if not path.exists():
        return None
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise PolicyError(f"invalid path-risk policy {path}: {exc}") from exc
    return _decode_policy(path, raw)


def validate_catalog_names(
    policy: PathRiskPolicy,
    *,
    profiles: Collection[str],
    checks: Collection[str],
) -> None:
    """Validate policy names against one exact configured verifier catalog."""
    configured_checks = tuple(checks)
    duplicate_checks = _duplicates(configured_checks)
    if duplicate_checks:
        raise PolicyError(f"duplicate configured check: {duplicate_checks[0]}")
    available_profiles = frozenset(profiles)
    available_checks = frozenset(configured_checks)
    for rule in policy.rules:
        unknown_profiles = sorted(set(rule.profiles) - available_profiles)
        if unknown_profiles:
            raise PolicyError(
                f"rule {rule.id!r} references unknown profile: {unknown_profiles[0]}",
            )
        unknown_checks = sorted(set(rule.checks) - available_checks)
        if unknown_checks:
            raise PolicyError(
                f"rule {rule.id!r} references unknown check: {unknown_checks[0]}",
            )


def _decode_policy(path: Path, raw: Mapping[str, object]) -> PathRiskPolicy:
    _reject_unknown(raw, TOP_LEVEL_KEYS, label="top-level")
    version = raw.get("version")
    if (
        not isinstance(version, int)
        or isinstance(version, bool)
        or version != POLICY_SCHEMA_VERSION
    ):
        raise PolicyError(f"version must be exactly {POLICY_SCHEMA_VERSION}")
    raw_rules = _object_list(raw.get("rules", []), label="rules")
    rules = tuple(_decode_rule(value, index) for index, value in enumerate(raw_rules))
    duplicate_rules = _duplicates(tuple(rule.id for rule in rules))
    if duplicate_rules:
        raise PolicyError(f"duplicate rule id: {duplicate_rules[0]}")
    return PathRiskPolicy(path=path.as_posix(), rules=rules, version=version)


def _decode_rule(value: object, index: int) -> PathRiskRule:
    label = f"rules[{index}]"
    raw = _table(value, label=label)
    _reject_unknown(raw, RULE_KEYS, label="rule")
    rule_id = _identifier(raw.get("id"), label=f"{label}.id")
    paths = _patterns(raw.get("paths"), label=f"{label}.paths")
    mode = raw.get("mode", "advisory")
    if not isinstance(mode, str) or mode not in VALID_MODES:
        raise PolicyError(f"{label}.mode must be advisory or required")
    evidence_values = _object_list(
        raw.get("evidence", []),
        label=f"{label}.evidence",
    )
    evidence = tuple(
        _decode_evidence(item, rule_index=index, evidence_index=evidence_index)
        for evidence_index, item in enumerate(evidence_values)
    )
    duplicate_evidence = _duplicates(tuple(item.id for item in evidence))
    if duplicate_evidence:
        raise PolicyError(
            f"duplicate evidence id in rule {rule_id!r}: {duplicate_evidence[0]}",
        )
    return PathRiskRule(
        id=rule_id,
        paths=paths,
        description=_optional_text(raw.get("description"), label=f"{label}.description"),
        mode=mode,
        profiles=_text_tuple(raw.get("profiles", []), label=f"{label}.profiles"),
        checks=_text_tuple(raw.get("checks", []), label=f"{label}.checks"),
        review_categories=_identifier_tuple(
            raw.get("review_categories", []),
            label=f"{label}.review_categories",
        ),
        evidence=evidence,
    )


def _decode_evidence(
    value: object,
    *,
    rule_index: int,
    evidence_index: int,
) -> EvidenceRequirement:
    label = f"rules[{rule_index}].evidence[{evidence_index}]"
    raw = _table(value, label=label)
    _reject_unknown(raw, EVIDENCE_KEYS, label="evidence")
    kind = raw.get("kind")
    if kind != CHANGED_PATH_KIND:
        raise PolicyError(f"{label}.kind must be {CHANGED_PATH_KIND!r}")
    minimum = raw.get("minimum", 1)
    if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 1:
        raise PolicyError(f"{label}.minimum must be a positive integer")
    return EvidenceRequirement(
        id=_identifier(raw.get("id"), label=f"{label}.id"),
        kind=CHANGED_PATH_KIND,
        paths=_patterns(raw.get("paths"), label=f"{label}.paths"),
        minimum=minimum,
        message=_optional_text(raw.get("message"), label=f"{label}.message"),
    )


def _patterns(value: object, *, label: str) -> tuple[str, ...]:
    patterns = _text_tuple(value, label=label, required=True)
    try:
        return tuple(validate_repo_pattern(pattern, label=label) for pattern in patterns)
    except PathPatternError as exc:
        raise PolicyError(str(exc)) from exc


def _identifier_tuple(value: object, *, label: str) -> tuple[str, ...]:
    values = _text_tuple(value, label=label)
    for item in values:
        if not IDENTIFIER.fullmatch(item):
            raise PolicyError(f"{label} contains invalid identifier: {item!r}")
    return values


def _text_tuple(
    value: object,
    *,
    label: str,
    required: bool = False,
) -> tuple[str, ...]:
    raw_values = _object_list(value, label=label, item_kind="text")
    if required and not raw_values:
        raise PolicyError(f"{label} must not be empty")
    values: list[str] = []
    for item in raw_values:
        if not isinstance(item, str) or not item:
            raise PolicyError(f"{label} must contain non-empty text")
        values.append(item)
    result = tuple(values)
    duplicates = _duplicates(result)
    if duplicates:
        raise PolicyError(f"{label} contains duplicate value: {duplicates[0]}")
    return result


def _identifier(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise PolicyError(f"{label} must be a kebab-case identifier")
    return value


def _optional_text(value: object, *, label: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str) or not value:
        raise PolicyError(f"{label} must be non-empty text")
    return value


def _table(value: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise PolicyError(f"{label} must be a table")
    return cast(Mapping[str, object], value)


def _object_list(
    value: object,
    *,
    label: str,
    item_kind: str = "tables",
) -> list[object]:
    if not isinstance(value, list):
        raise PolicyError(f"{label} must be an array of {item_kind}")
    return cast(list[object], value)


def _reject_unknown(
    raw: Mapping[str, object],
    allowed: frozenset[str],
    *,
    label: str,
) -> None:
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise PolicyError(f"unknown {label} key: {unknown[0]}")


def _duplicates(values: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return tuple(sorted(duplicates))


# docsync:evidence.end evidence.readme.path_risk_policy
