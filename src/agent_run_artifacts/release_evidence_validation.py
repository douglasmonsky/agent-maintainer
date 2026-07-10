"""Validation for self-contained exact-commit release evidence."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import cast

from agent_run_artifacts import release_evidence_contract as contract
from agent_run_artifacts import release_profile_evidence


def validate_release_evidence(
    evidence: Mapping[str, object],
    *,
    expected_sha: str,
    now: datetime | None = None,
) -> None:
    """Validate self-contained aggregate evidence for one exact commit."""

    checked_now = contract.checked_now(now)
    expires_at = _validate_header(
        evidence,
        expected_sha=expected_sha,
        now=checked_now,
    )
    entries = _profile_entries(evidence.get("profiles"))
    validated = [
        _validate_profile_entry(
            entry,
            expected_profile=profile,
            expected_sha=expected_sha,
            now=checked_now,
        )
        for profile, entry in zip(contract.REQUIRED_PROFILES, entries, strict=True)
    ]
    expected_expiry = min(profile.generated_at + contract.MAX_EVIDENCE_AGE for profile in validated)
    if expires_at != expected_expiry:
        raise contract.ReleaseEvidenceError("release evidence expiry does not match profile window")


def _validate_header(
    evidence: Mapping[str, object],
    *,
    expected_sha: str,
    now: datetime,
) -> datetime:
    contract.validate_sha(expected_sha, label="expected commit")
    _validate_schema(evidence)
    _validate_commit(evidence, expected_sha=expected_sha)
    return _validate_window(evidence, now=now)


def _validate_schema(evidence: Mapping[str, object]) -> None:
    if evidence.get("version") != contract.RELEASE_EVIDENCE_VERSION:
        raise contract.ReleaseEvidenceError("unsupported release evidence version")
    if evidence.get("kind") != contract.RELEASE_EVIDENCE_KIND:
        raise contract.ReleaseEvidenceError("unexpected release evidence kind")
    if evidence.get("required_profiles") != list(contract.REQUIRED_PROFILES):
        raise contract.ReleaseEvidenceError("release evidence required_profiles is invalid")


def _validate_commit(
    evidence: Mapping[str, object],
    *,
    expected_sha: str,
) -> None:
    commit = contract.required_text(evidence.get("commit"), "release evidence commit")
    contract.validate_sha(commit, label="release evidence commit")
    if commit != expected_sha:
        raise contract.ReleaseEvidenceError(
            "release evidence commit does not match expected commit"
        )


def _validate_window(
    evidence: Mapping[str, object],
    *,
    now: datetime,
) -> datetime:
    generated_at = contract.parse_time(
        evidence.get("generated_at"),
        label="release evidence generated_at",
    )
    expires_at = contract.parse_time(
        evidence.get("expires_at"),
        label="release evidence expires_at",
    )
    if generated_at > now + contract.MAX_CLOCK_SKEW:
        raise contract.ReleaseEvidenceError("release evidence is dated in the future")
    if now > expires_at:
        raise contract.ReleaseEvidenceError("release evidence expired")
    if expires_at < generated_at:
        raise contract.ReleaseEvidenceError("release evidence expires before generation")
    return expires_at


def _profile_entries(value: object) -> list[object]:
    if not isinstance(value, list):
        raise contract.ReleaseEvidenceError(_profile_count_message())
    entries = cast(list[object], value)
    if len(entries) != len(contract.REQUIRED_PROFILES):
        raise contract.ReleaseEvidenceError(_profile_count_message())
    return entries


def _profile_count_message() -> str:
    return f"release evidence profiles must contain {len(contract.REQUIRED_PROFILES)} entries"


def _validate_profile_entry(
    value: object,
    *,
    expected_profile: str,
    expected_sha: str,
    now: datetime,
) -> contract.ValidatedProfile:
    profile, entry = _validated_entry_identity(value, expected_profile=expected_profile)
    manifest = _validated_entry_manifest(entry, profile=profile)
    validated = release_profile_evidence.validate_profile_manifest(
        manifest,
        expected_sha=expected_sha,
        now=now,
    )
    if validated.profile != profile:
        raise contract.ReleaseEvidenceError(f"profile {profile} entry does not match its manifest")
    return validated


def _validated_entry_identity(
    value: object,
    *,
    expected_profile: str,
) -> tuple[str, Mapping[str, object]]:
    entry = contract.required_mapping(
        value,
        f"release evidence profile entry {expected_profile}",
    )
    profile = contract.required_text(
        entry.get("profile"),
        "release evidence entry profile",
    )
    if profile != expected_profile:
        message = (
            f"release evidence profile order mismatch: expected {expected_profile}, got {profile}"
        )
        raise contract.ReleaseEvidenceError(message)
    return profile, entry


def _validated_entry_manifest(
    entry: Mapping[str, object],
    *,
    profile: str,
) -> Mapping[str, object]:
    manifest = contract.required_mapping(
        entry.get("manifest"),
        f"release evidence profile {profile} manifest",
    )
    digest = contract.required_text(
        entry.get("sha256"),
        f"release evidence profile {profile} sha256",
    )
    if contract.FULL_SHA256.fullmatch(digest) is None:
        raise contract.ReleaseEvidenceError(f"profile {profile} digest is malformed")
    if contract.manifest_sha256(manifest) != digest:
        raise contract.ReleaseEvidenceError(f"profile {profile} digest mismatch")
    return manifest
