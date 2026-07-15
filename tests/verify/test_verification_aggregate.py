"""Tests for deterministic partial verifier manifest aggregation."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import cast

import pytest

from agent_run_artifacts.verification_aggregate import (
    VerificationAggregateError,
    aggregate_partial_manifests,
)

GROUPS = ("tests-and-coverage", "static-and-policy")


def partial_manifest(group: str, check_name: str) -> dict[str, object]:
    """Return a minimal valid partial manifest."""

    return {
        "version": 1,
        "run_id": f"run-{group}",
        "generated_at": "2026-07-15T12:00:00Z",
        "profile": "ci",
        "base_ref": "origin/main",
        "compare_branch": "origin/main",
        "staged": False,
        "failure_snapshot": "",
        "git": {"branch": "feature", "dirty": False, "sha": "abc123"},
        "timing": {
            "duration_seconds": 1.0,
            "ended_at": "2026-07-15T12:00:00Z",
            "started_at": "2026-07-15T11:59:59Z",
        },
        "expected_duration_hint": "expected CI-equivalent check",
        "thresholds": {"coverage_fail_under": 90},
        "checks": [{"name": check_name, "status": "passed"}],
        "partial": {
            "group": group,
            "required_groups": list(GROUPS),
            "identity": {
                "profile": "ci",
                "head": "abc123",
                "base_ref": "origin/main",
                "compare_branch": "origin/main",
                "staged": False,
                "index_hash": "index-hash",
                "worktree_hash": "worktree-hash",
                "untracked_hash": "untracked-hash",
                "config_hash": "config-hash",
                "environment_hash": "environment-hash",
                "selected_checks": [check_name],
            },
        },
    }


def write_manifest(path: Path, payload: dict[str, object]) -> Path:
    """Write one manifest fixture."""

    path.write_text(f"{json.dumps(payload)}\n", encoding="utf-8")
    return path


def valid_paths(tmp_path: Path) -> tuple[Path, Path]:
    """Write both required group manifests."""

    tests_path = write_manifest(
        tmp_path / "tests.json",
        partial_manifest("tests-and-coverage", "pytest-coverage"),
    )
    static_path = write_manifest(
        tmp_path / "static.json",
        partial_manifest("static-and-policy", "ruff"),
    )
    return tests_path, static_path


def test_aggregate_is_deterministic_and_uses_group_order(tmp_path: Path) -> None:
    tests_path, static_path = valid_paths(tmp_path)

    forward = aggregate_partial_manifests([tests_path, static_path])
    reversed_result = aggregate_partial_manifests([static_path, tests_path])

    assert forward == reversed_result
    checks = cast(list[dict[str, object]], forward["checks"])
    assert [check["name"] for check in checks] == ["pytest-coverage", "ruff"]
    assert forward["aggregate"] == {
        "groups": list(GROUPS),
        "partial_run_ids": ["run-tests-and-coverage", "run-static-and-policy"],
    }


def test_missing_group_fails_closed(tmp_path: Path) -> None:
    tests_path, _static_path = valid_paths(tmp_path)

    with pytest.raises(VerificationAggregateError, match="missing groups: static-and-policy"):
        aggregate_partial_manifests([tests_path])


def test_required_group_contract_cannot_be_narrowed(tmp_path: Path) -> None:
    narrowed = partial_manifest("tests-and-coverage", "pytest-coverage")
    partial = cast(dict[str, object], narrowed["partial"])
    partial["required_groups"] = ["tests-and-coverage"]
    path = write_manifest(tmp_path / "narrowed.json", narrowed)

    with pytest.raises(VerificationAggregateError, match="required group identity mismatch"):
        aggregate_partial_manifests([path])


def test_duplicate_group_fails_closed(tmp_path: Path) -> None:
    tests_path, _static_path = valid_paths(tmp_path)
    duplicate = write_manifest(
        tmp_path / "duplicate.json",
        partial_manifest("tests-and-coverage", "diff-cover"),
    )

    with pytest.raises(VerificationAggregateError, match="duplicate group: tests-and-coverage"):
        aggregate_partial_manifests([tests_path, duplicate])


def test_identity_mismatch_fails_closed(tmp_path: Path) -> None:
    tests_path, static_path = valid_paths(tmp_path)
    static = json.loads(static_path.read_text(encoding="utf-8"))
    static["partial"]["identity"]["config_hash"] = "changed"
    write_manifest(static_path, static)

    with pytest.raises(VerificationAggregateError, match="identity mismatch"):
        aggregate_partial_manifests([tests_path, static_path])


@pytest.mark.parametrize(
    ("key", "changed_value"),
    (
        ("staged", True),
        ("index_hash", "changed-index"),
        ("worktree_hash", "changed-worktree"),
        ("untracked_hash", "changed-untracked"),
        ("environment_hash", "changed-environment"),
    ),
)
def test_repository_state_identity_mismatch_fails_closed(
    tmp_path: Path,
    key: str,
    changed_value: object,
) -> None:
    """Partial runs from different exact repository states cannot combine."""

    tests_path, static_path = valid_paths(tmp_path)
    static = json.loads(static_path.read_text(encoding="utf-8"))
    static["partial"]["identity"][key] = changed_value
    if key == "staged":
        static["staged"] = changed_value
    write_manifest(static_path, static)

    with pytest.raises(VerificationAggregateError, match="partial identity mismatch"):
        aggregate_partial_manifests([tests_path, static_path])


def test_top_level_staged_state_must_match_partial_identity(tmp_path: Path) -> None:
    """A manifest cannot contradict the staged mode bound into its identity."""

    tests_path, static_path = valid_paths(tmp_path)
    static = json.loads(static_path.read_text(encoding="utf-8"))
    static["staged"] = True
    write_manifest(static_path, static)

    with pytest.raises(VerificationAggregateError, match="manifest identity mismatch"):
        aggregate_partial_manifests([tests_path, static_path])


def test_top_level_metadata_must_match_partial_identity(tmp_path: Path) -> None:
    tests_path, static_path = valid_paths(tmp_path)
    static = json.loads(static_path.read_text(encoding="utf-8"))
    static["base_ref"] = "other-branch"
    write_manifest(static_path, static)

    with pytest.raises(VerificationAggregateError, match="manifest identity mismatch"):
        aggregate_partial_manifests([tests_path, static_path])


def test_failed_partial_fails_closed(tmp_path: Path) -> None:
    tests_path, static_path = valid_paths(tmp_path)
    failed = json.loads(tests_path.read_text(encoding="utf-8"))
    failed["checks"][0]["status"] = "failed"
    write_manifest(tests_path, failed)

    with pytest.raises(VerificationAggregateError, match="failed check: pytest-coverage"):
        aggregate_partial_manifests([tests_path, static_path])


def test_duplicate_check_across_groups_fails_closed(tmp_path: Path) -> None:
    tests_path, static_path = valid_paths(tmp_path)
    static = deepcopy(partial_manifest("static-and-policy", "pytest-coverage"))
    write_manifest(static_path, static)

    with pytest.raises(VerificationAggregateError, match="duplicate check: pytest-coverage"):
        aggregate_partial_manifests([tests_path, static_path])
