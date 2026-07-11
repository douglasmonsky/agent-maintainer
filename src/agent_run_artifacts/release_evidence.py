"""Public exact-commit release evidence contracts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime

from agent_run_artifacts import release_evidence_contract as contract
from agent_run_artifacts import release_evidence_validation as aggregate_validation
from agent_run_artifacts import release_profile_evidence as profile_validation

CommandProfileRun = contract.CommandProfileRun
MAX_EVIDENCE_AGE = contract.MAX_EVIDENCE_AGE
REQUIRED_PROFILES = contract.REQUIRED_PROFILES
ReleaseEvidenceError = contract.ReleaseEvidenceError
ValidatedProfile = contract.ValidatedProfile
manifest_sha256 = contract.manifest_sha256
validate_profile_manifest = profile_validation.validate_profile_manifest
validate_release_evidence = aggregate_validation.validate_release_evidence


def aggregate_profile_manifests(
    manifests: Sequence[Mapping[str, object]],
    *,
    expected_sha: str,
    now: datetime | None = None,
) -> dict[str, object]:
    """Return self-contained evidence for one complete profile matrix."""

    checked_now = contract.checked_now(now)
    contract.validate_sha(expected_sha, label="expected commit")
    by_profile = _validated_profiles(
        manifests,
        expected_sha=expected_sha,
        now=checked_now,
    )
    _require_complete_profiles(by_profile)
    aggregate = _aggregate_payload(
        by_profile,
        expected_sha=expected_sha,
        now=checked_now,
    )
    validate_release_evidence(
        aggregate,
        expected_sha=expected_sha,
        now=checked_now,
    )
    return aggregate


def _validated_profiles(
    manifests: Sequence[Mapping[str, object]],
    *,
    expected_sha: str,
    now: datetime,
) -> dict[str, contract.ProfileRecord]:
    by_profile: dict[str, contract.ProfileRecord] = {}
    for raw_manifest in manifests:
        manifest = dict(raw_manifest)
        validated = validate_profile_manifest(
            manifest,
            expected_sha=expected_sha,
            now=now,
        )
        profile = validated.profile
        if profile in by_profile:
            raise ReleaseEvidenceError(f"duplicate profile manifest: {profile}")
        by_profile[profile] = contract.ProfileRecord(manifest, validated)
    return by_profile


def _require_complete_profiles(
    by_profile: Mapping[str, contract.ProfileRecord],
) -> None:
    missing = [profile for profile in REQUIRED_PROFILES if profile not in by_profile]
    if missing:
        missing_profiles = ", ".join(missing)
        raise ReleaseEvidenceError(f"missing required profiles: {missing_profiles}")


def _aggregate_payload(
    by_profile: Mapping[str, contract.ProfileRecord],
    *,
    expected_sha: str,
    now: datetime,
) -> dict[str, object]:
    entries = [
        {
            "profile": profile,
            "sha256": manifest_sha256(by_profile[profile].manifest),
            "manifest": by_profile[profile].manifest,
        }
        for profile in REQUIRED_PROFILES
    ]
    expires_at = min(
        record.validated.generated_at + MAX_EVIDENCE_AGE for record in by_profile.values()
    )
    return {
        "version": contract.RELEASE_EVIDENCE_VERSION,
        "kind": contract.RELEASE_EVIDENCE_KIND,
        "commit": expected_sha,
        "generated_at": contract.format_time(now),
        "expires_at": contract.format_time(expires_at),
        "required_profiles": list(REQUIRED_PROFILES),
        "profiles": entries,
    }


def command_profile_manifest(run: CommandProfileRun) -> dict[str, object]:
    """Return a verifier-compatible manifest for one external profile command."""

    status = "passed" if run.exit_code == 0 else "failed"
    started = contract.checked_datetime(run.started_at, label="command started_at")
    ended = contract.checked_datetime(run.ended_at, label="command ended_at")
    if ended < started:
        raise ReleaseEvidenceError("command ended before it started")
    return {
        "version": contract.PROFILE_MANIFEST_VERSION,
        "profile": run.profile,
        "run_id": f"{run.profile}-{ended.strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": contract.format_time(ended),
        "git": dict(run.git),
        "checks": [
            {
                "name": f"{run.profile}-check",
                "status": status,
                "command": list(run.command),
                "exit_code": run.exit_code,
                "started_at": contract.format_time(started),
                "ended_at": contract.format_time(ended),
            }
        ],
        "timing": {
            "started_at": contract.format_time(started),
            "ended_at": contract.format_time(ended),
            "duration_seconds": max(
                (ended - started).total_seconds(),
                contract.ZERO_SECONDS,
            ),
        },
    }
