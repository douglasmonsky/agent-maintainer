"""Tests exact-commit release evidence aggregation and validation."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest

from agent_run_artifacts import release_evidence

COMMIT_SHA = "a" * 40
OTHER_SHA = "b" * 40
NOW = datetime(2026, 7, 10, 18, 0, tzinfo=UTC)
ManifestMutator = Callable[[list[dict[str, object]]], object]


def profile_manifest(
    profile: str,
    *,
    sha: str = COMMIT_SHA,
    dirty: bool = False,
    status: str = "passed",
    generated_at: datetime = NOW,
) -> dict[str, object]:
    """Return one minimal verifier-compatible profile manifest."""

    timestamp = generated_at.isoformat().replace("+00:00", "Z")
    return {
        "version": 1,
        "profile": profile,
        "run_id": f"run-{profile}",
        "generated_at": timestamp,
        "git": {
            "sha": sha,
            "branch": "main",
            "dirty": dirty,
        },
        "checks": [
            {
                "name": f"{profile}-check",
                "status": status,
                "exit_code": 0 if status == "passed" else 1,
            },
        ],
    }


def required_manifests() -> list[dict[str, object]]:
    """Return a complete exact-commit profile matrix."""

    return [profile_manifest(profile) for profile in release_evidence.REQUIRED_PROFILES]


def remove_release(manifests: list[dict[str, object]]) -> object:
    """Remove the final required profile."""

    return manifests.pop()


def duplicate_full(manifests: list[dict[str, object]]) -> object:
    """Append a duplicate full profile."""

    manifests.append(profile_manifest("full"))
    return None


def replace_full_with_fast(manifests: list[dict[str, object]]) -> object:
    """Replace a required profile name with an unsupported profile."""

    manifests[0]["profile"] = "fast"
    return None


def replace_full_commit(manifests: list[dict[str, object]]) -> object:
    """Substitute another commit into the full manifest."""

    manifests[0]["git"] = {"sha": OTHER_SHA, "branch": "main", "dirty": False}
    return None


def mark_full_dirty(manifests: list[dict[str, object]]) -> object:
    """Mark the full profile worktree dirty."""

    manifests[0]["git"] = {"sha": COMMIT_SHA, "branch": "main", "dirty": True}
    return None


def fail_full_check(manifests: list[dict[str, object]]) -> object:
    """Replace the full profile check with a failure."""

    manifests[0]["checks"] = [
        {"name": "full-check", "status": "failed", "exit_code": 1},
    ]
    return None


def remove_full_checks(manifests: list[dict[str, object]]) -> object:
    """Remove every check from the full profile."""

    manifests[0]["checks"] = []
    return None


def replace_full_schema_version(manifests: list[dict[str, object]]) -> object:
    """Use an unsupported profile manifest version."""

    manifests[0]["version"] = 2
    return None


def test_aggregate_accepts_complete_exact_commit_matrix() -> None:
    """Every required clean passing profile produces self-contained evidence."""

    aggregate = release_evidence.aggregate_profile_manifests(
        required_manifests(),
        expected_sha=COMMIT_SHA,
        now=NOW,
    )

    release_evidence.validate_release_evidence(
        aggregate,
        expected_sha=COMMIT_SHA,
        now=NOW,
    )
    assert aggregate["commit"] == COMMIT_SHA
    assert aggregate["required_profiles"] == list(release_evidence.REQUIRED_PROFILES)
    entries = cast(list[object], aggregate["profiles"])
    profile_names = [
        cast(dict[str, object], entry)["profile"] for entry in entries if isinstance(entry, dict)
    ]
    assert profile_names == list(release_evidence.REQUIRED_PROFILES)


@pytest.mark.parametrize(
    ("mutate", "message"),
    (
        (
            remove_release,
            "missing required profiles: release",
        ),
        (
            duplicate_full,
            "duplicate profile manifest: full",
        ),
        (
            replace_full_with_fast,
            "unexpected profile: fast",
        ),
        (
            replace_full_commit,
            "profile full commit does not match expected commit",
        ),
        (
            mark_full_dirty,
            "profile full was produced from a dirty worktree",
        ),
        (
            fail_full_check,
            "profile full contains failed check: full-check",
        ),
        (
            remove_full_checks,
            "profile full checks must be a non-empty list",
        ),
        (
            replace_full_schema_version,
            "profile full has unsupported manifest version",
        ),
    ),
)
def test_aggregate_rejects_incomplete_or_untrusted_profiles(
    mutate: ManifestMutator,
    message: str,
) -> None:
    """Partial, mixed, dirty, failed, and malformed evidence fails closed."""

    manifests = required_manifests()
    mutate(manifests)

    with pytest.raises(release_evidence.ReleaseEvidenceError, match=message):
        release_evidence.aggregate_profile_manifests(
            manifests,
            expected_sha=COMMIT_SHA,
            now=NOW,
        )


def test_aggregate_rejects_stale_profile_manifest() -> None:
    """Evidence cannot outlive the configured release window."""

    manifests = required_manifests()
    manifests[0] = profile_manifest(
        "full",
        generated_at=NOW - release_evidence.MAX_EVIDENCE_AGE - timedelta(seconds=1),
    )

    with pytest.raises(release_evidence.ReleaseEvidenceError, match="profile full is stale"):
        release_evidence.aggregate_profile_manifests(
            manifests,
            expected_sha=COMMIT_SHA,
            now=NOW,
        )


def test_validate_rejects_tampered_embedded_manifest() -> None:
    """Changing embedded profile evidence invalidates its recorded digest."""

    aggregate = release_evidence.aggregate_profile_manifests(
        required_manifests(),
        expected_sha=COMMIT_SHA,
        now=NOW,
    )
    tampered = deepcopy(aggregate)
    entries = cast(list[object], tampered["profiles"])
    first = entries[0]
    assert isinstance(first, dict)
    first_entry = cast(dict[str, object], first)
    manifest = first_entry["manifest"]
    assert isinstance(manifest, dict)
    cast(dict[str, object], manifest)["run_id"] = "substituted-run"

    with pytest.raises(release_evidence.ReleaseEvidenceError, match="digest mismatch"):
        release_evidence.validate_release_evidence(
            tampered,
            expected_sha=COMMIT_SHA,
            now=NOW,
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("version", 2, "unsupported release evidence version"),
        ("commit", OTHER_SHA, "release evidence commit does not match expected commit"),
        ("kind", "other", "unexpected release evidence kind"),
        ("profiles", [], "release evidence profiles must contain 5 entries"),
    ),
)
def test_validate_rejects_malformed_aggregate(
    field: str,
    value: object,
    message: str,
) -> None:
    """Aggregate schema and exact-commit fields are fail-closed."""

    aggregate = release_evidence.aggregate_profile_manifests(
        required_manifests(),
        expected_sha=COMMIT_SHA,
        now=NOW,
    )
    aggregate[field] = value

    with pytest.raises(release_evidence.ReleaseEvidenceError, match=message):
        release_evidence.validate_release_evidence(
            aggregate,
            expected_sha=COMMIT_SHA,
            now=NOW,
        )


def test_validate_rejects_expired_aggregate() -> None:
    """A once-valid aggregate cannot be reused after its profile window expires."""

    aggregate = release_evidence.aggregate_profile_manifests(
        required_manifests(),
        expected_sha=COMMIT_SHA,
        now=NOW,
    )

    with pytest.raises(release_evidence.ReleaseEvidenceError, match="release evidence expired"):
        release_evidence.validate_release_evidence(
            aggregate,
            expected_sha=COMMIT_SHA,
            now=NOW + release_evidence.MAX_EVIDENCE_AGE + timedelta(seconds=1),
        )


def test_command_profile_manifest_records_terminal_status() -> None:
    """Release-only commands use the same strict profile manifest contract."""

    passed = release_evidence.command_profile_manifest(
        release_evidence.CommandProfileRun(
            profile="release",
            command=("just", "release-check"),
            exit_code=0,
            git={"sha": COMMIT_SHA, "branch": "main", "dirty": False},
            started_at=NOW,
            ended_at=NOW + timedelta(seconds=2),
        )
    )
    failed = release_evidence.command_profile_manifest(
        release_evidence.CommandProfileRun(
            profile="release",
            command=("just", "release-check"),
            exit_code=2,
            git={"sha": COMMIT_SHA, "branch": "main", "dirty": False},
            started_at=NOW,
            ended_at=NOW + timedelta(seconds=2),
        )
    )

    release_evidence.validate_profile_manifest(
        passed,
        expected_sha=COMMIT_SHA,
        now=NOW + timedelta(seconds=2),
    )
    with pytest.raises(release_evidence.ReleaseEvidenceError, match="contains failed check"):
        release_evidence.validate_profile_manifest(
            failed,
            expected_sha=COMMIT_SHA,
            now=NOW + timedelta(seconds=2),
        )
