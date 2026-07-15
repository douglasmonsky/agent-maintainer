"""Fail-closed aggregation for verifier partial manifests."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

_ALLOWED_CHECK_STATUSES = frozenset(
    (
        "passed",
        "skipped-disabled",
        "skipped-missing-optional",
        "skipped-not-applicable",
        "skipped-required",
        "skipped-unsafe-config",
        "warning",
    )
)
_SHARED_IDENTITY_KEYS = ("profile", "head", "base_ref", "compare_branch", "config_hash")
REQUIRED_GROUPS = ("tests-and-coverage", "static-and-policy")


class VerificationAggregateError(ValueError):
    """Raised when partial verifier evidence is incomplete or inconsistent."""


def aggregate_partial_manifests(paths: Sequence[Path]) -> dict[str, object]:
    """Return one deterministic manifest from complete compatible partials."""

    manifests = [_load_manifest(path) for path in paths]
    by_group, required_groups = _index_groups(manifests)
    ordered = _ordered_manifests(by_group, required_groups)
    _validate_shared_state(ordered)
    checks = _combined_checks(ordered)
    first = ordered[0]
    return {
        **_shared_manifest_fields(first),
        "run_id": _aggregate_run_id(ordered),
        "generated_at": max(_text(item, "generated_at") for item in ordered),
        "failure_snapshot": "",
        "timing": _aggregate_timing(ordered),
        "checks": checks,
        "aggregate": {
            "groups": list(required_groups),
            "partial_run_ids": [_text(item, "run_id") for item in ordered],
        },
    }


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VerificationAggregateError(f"invalid partial manifest: {path}") from exc
    if not isinstance(payload, dict):
        raise VerificationAggregateError(f"partial manifest is not an object: {path}")
    return cast(dict[str, Any], payload)


def _index_groups(
    manifests: Sequence[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], tuple[str, ...]]:
    if not manifests:
        raise VerificationAggregateError("no partial manifests provided")
    by_group: dict[str, dict[str, Any]] = {}
    for manifest in manifests:
        partial = _mapping(manifest, "partial")
        group = _text(partial, "group")
        current_required = _string_tuple(partial, "required_groups")
        if current_required != REQUIRED_GROUPS:
            raise VerificationAggregateError("required group identity mismatch")
        if group in by_group:
            raise VerificationAggregateError(f"duplicate group: {group}")
        by_group[group] = manifest
    return by_group, REQUIRED_GROUPS


def _ordered_manifests(
    by_group: Mapping[str, dict[str, Any]], required_groups: tuple[str, ...]
) -> list[dict[str, Any]]:
    missing = [group for group in required_groups if group not in by_group]
    extra = [group for group in by_group if group not in required_groups]
    if missing:
        raise VerificationAggregateError(f"missing groups: {', '.join(missing)}")
    if extra:
        raise VerificationAggregateError(f"unexpected groups: {', '.join(sorted(extra))}")
    return [by_group[group] for group in required_groups]


def _validate_shared_state(manifests: Sequence[dict[str, Any]]) -> None:
    expected_identity = _shared_identity(manifests[0])
    expected_thresholds = manifests[0].get("thresholds")
    for manifest in manifests:
        _validate_manifest_identity(manifest)
        if _shared_identity(manifest) != expected_identity:
            raise VerificationAggregateError("partial identity mismatch")
        if manifest.get("thresholds") != expected_thresholds:
            raise VerificationAggregateError("threshold identity mismatch")


def _shared_identity(manifest: Mapping[str, Any]) -> tuple[object, ...]:
    identity = _mapping(_mapping(manifest, "partial"), "identity")
    return tuple(_text(identity, key) for key in _SHARED_IDENTITY_KEYS)


def _validate_manifest_identity(manifest: Mapping[str, Any]) -> None:
    identity = _mapping(_mapping(manifest, "partial"), "identity")
    for key in ("profile", "base_ref", "compare_branch"):
        if manifest.get(key) != _text(identity, key):
            raise VerificationAggregateError("manifest identity mismatch")
    git = _mapping(manifest, "git")
    if git.get("sha") != _text(identity, "head"):
        raise VerificationAggregateError("manifest identity mismatch")


def _combined_checks(manifests: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    combined: list[dict[str, Any]] = []
    seen: set[str] = set()
    for manifest in manifests:
        checks = _check_objects(manifest)
        _validate_selected_checks(manifest, checks)
        for check in checks:
            name = _text(check, "name")
            if name in seen:
                raise VerificationAggregateError(f"duplicate check: {name}")
            _validate_check_status(check, name)
            seen.add(name)
            combined.append(check)
    return combined


def _check_objects(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_checks = manifest.get("checks")
    if not isinstance(raw_checks, list):
        raise VerificationAggregateError("checks must be a list of objects")
    check_items = cast(list[object], raw_checks)
    if not all(isinstance(item, dict) for item in check_items):
        raise VerificationAggregateError("checks must be a list of objects")
    return [cast(dict[str, Any], item) for item in check_items]


def _validate_selected_checks(
    manifest: Mapping[str, Any], checks: Sequence[Mapping[str, Any]]
) -> None:
    identity = _mapping(_mapping(manifest, "partial"), "identity")
    selected = _string_tuple(identity, "selected_checks")
    actual = tuple(_text(check, "name") for check in checks)
    if selected != actual:
        raise VerificationAggregateError("selected check identity mismatch")


def _validate_check_status(check: Mapping[str, Any], name: str) -> None:
    status = _text(check, "status")
    if status not in _ALLOWED_CHECK_STATUSES:
        raise VerificationAggregateError(f"failed check: {name}")


def _shared_manifest_fields(manifest: Mapping[str, Any]) -> dict[str, object]:
    fields = (
        "version",
        "profile",
        "base_ref",
        "compare_branch",
        "staged",
        "git",
        "expected_duration_hint",
        "thresholds",
    )
    return {field: manifest.get(field) for field in fields}


def _aggregate_run_id(manifests: Sequence[Mapping[str, Any]]) -> str:
    identity = [
        {
            "group": _text(_mapping(item, "partial"), "group"),
            "run_id": _text(item, "run_id"),
        }
        for item in manifests
    ]
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return f"aggregate-{digest[:12]}"


def _aggregate_timing(manifests: Sequence[Mapping[str, Any]]) -> dict[str, object]:
    timings = [_mapping(item, "timing") for item in manifests]
    return {
        "duration_seconds": sum(float(item.get("duration_seconds", 0.0)) for item in timings),
        "ended_at": max(_text(item, "ended_at") for item in timings),
        "started_at": min(_text(item, "started_at") for item in timings),
    }


def _mapping(payload: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise VerificationAggregateError(f"{key} must be an object")
    return cast(dict[str, Any], value)


def _text(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise VerificationAggregateError(f"{key} must be a non-empty string")
    return value


def _string_tuple(payload: Mapping[str, Any], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise VerificationAggregateError(f"{key} must be a non-empty string list")
    items = cast(list[object], value)
    if not items or not all(isinstance(item, str) for item in items):
        raise VerificationAggregateError(f"{key} must be a non-empty string list")
    return tuple(cast(str, item) for item in items)
