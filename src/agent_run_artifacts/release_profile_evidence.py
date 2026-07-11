"""Validation for one verifier-compatible release profile manifest."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import cast

from agent_run_artifacts import release_evidence_contract as contract


def validate_profile_manifest(
    manifest: Mapping[str, object],
    *,
    expected_sha: str,
    now: datetime | None = None,
) -> contract.ValidatedProfile:
    """Validate one clean, passing, recent profile manifest."""

    checked_now = contract.checked_now(now)
    contract.validate_sha(expected_sha, label="expected commit")
    profile = _validate_identity(manifest)
    _validate_git(manifest, profile=profile, expected_sha=expected_sha)
    _validate_checks(manifest.get("checks"), profile=profile)
    generated_at = _validate_time(manifest, profile=profile, now=checked_now)
    return contract.ValidatedProfile(profile=profile, generated_at=generated_at)


def _validate_identity(manifest: Mapping[str, object]) -> str:
    profile = contract.required_text(manifest.get("profile"), "profile manifest profile")
    if profile not in contract.REQUIRED_PROFILES:
        raise contract.ReleaseEvidenceError(f"unexpected profile: {profile}")
    if manifest.get("version") != contract.PROFILE_MANIFEST_VERSION:
        raise contract.ReleaseEvidenceError(f"profile {profile} has unsupported manifest version")
    contract.required_text(manifest.get("run_id"), f"profile {profile} run_id")
    return profile


def _validate_git(
    manifest: Mapping[str, object],
    *,
    profile: str,
    expected_sha: str,
) -> None:
    git = contract.required_mapping(manifest.get("git"), f"profile {profile} git")
    actual_sha = contract.required_text(git.get("sha"), f"profile {profile} git.sha")
    contract.validate_sha(actual_sha, label=f"profile {profile} commit")
    if actual_sha != expected_sha:
        raise contract.ReleaseEvidenceError(
            f"profile {profile} commit does not match expected commit"
        )
    if git.get("dirty") is not False:
        raise contract.ReleaseEvidenceError(f"profile {profile} was produced from a dirty worktree")


def _validate_time(
    manifest: Mapping[str, object],
    *,
    profile: str,
    now: datetime,
) -> datetime:
    generated_at = contract.parse_time(
        manifest.get("generated_at"),
        label=f"profile {profile} generated_at",
    )
    if generated_at > now + contract.MAX_CLOCK_SKEW:
        raise contract.ReleaseEvidenceError(f"profile {profile} is dated in the future")
    if now - generated_at > contract.MAX_EVIDENCE_AGE:
        raise contract.ReleaseEvidenceError(f"profile {profile} is stale")
    return generated_at


def _validate_checks(value: object, *, profile: str) -> None:
    checks = _required_checks(value, profile=profile)
    names: set[str] = set()
    passed = False
    for raw_check in checks:
        check = contract.required_mapping(raw_check, f"profile {profile} check")
        name = _validated_check_name(check, profile=profile, names=names)
        status = _validated_check_status(check, profile=profile, name=name)
        passed = passed or status == "passed"
    if not passed:
        raise contract.ReleaseEvidenceError(f"profile {profile} contains no passed checks")


def _required_checks(value: object, *, profile: str) -> list[object]:
    if not isinstance(value, list) or not value:
        raise contract.ReleaseEvidenceError(f"profile {profile} checks must be a non-empty list")
    return cast(list[object], value)


def _validated_check_name(
    check: Mapping[str, object],
    *,
    profile: str,
    names: set[str],
) -> str:
    name = contract.required_text(check.get("name"), f"profile {profile} check name")
    if name in names:
        raise contract.ReleaseEvidenceError(f"profile {profile} has duplicate check: {name}")
    names.add(name)
    return name


def _validated_check_status(
    check: Mapping[str, object],
    *,
    profile: str,
    name: str,
) -> str:
    status = contract.required_text(
        check.get("status"),
        f"profile {profile} check {name} status",
    )
    if status == "failed":
        raise contract.ReleaseEvidenceError(f"profile {profile} contains failed check: {name}")
    if status not in contract.SUCCESS_CHECK_STATUSES:
        raise contract.ReleaseEvidenceError(
            f"profile {profile} check {name} has unsupported status: {status}"
        )
    return status
