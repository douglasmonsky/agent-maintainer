"""Tests context pack artifact upload doctor policy."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer.config import schema
from agent_maintainer.doctor.support import context_artifacts
from agent_maintainer.doctor.support import models as doctor_models


def test_context_pack_upload_policy_warns_on_broad_verify_logs_upload(
    tmp_path: Path,
) -> None:
    """Broad .verify-logs uploads can include local-only context packs."""

    write_workflow(
        tmp_path,
        """
        name: verify
        jobs:
          verify:
            steps:
              - uses: actions/upload-artifact@v6
                with:
                  name: verify-logs
                  path: .verify-logs/
        """,
    )

    result = context_artifacts.check_context_pack_upload_policy(tmp_path, schema.MaintainerConfig())

    assert result.status == doctor_models.WARNING
    assert result.state == doctor_models.UNSAFE_CONFIG
    assert ".github/workflows/verify.yml" in result.message
    assert ".verify-logs/context/**" in result.hint


def test_context_pack_upload_policy_accepts_explicit_safe_paths(
    tmp_path: Path,
) -> None:
    """Explicit top-level artifacts with context exclusion are upload-safe."""

    write_workflow(
        tmp_path,
        """
        name: verify
        jobs:
          verify:
            steps:
              - uses: actions/upload-artifact@v6
                with:
                  name: verify-logs
                  path: |
                    .verify-logs/manifest.json
                    .verify-logs/LAST_FAILURE.md
                    .verify-logs/*.log
                    .verify-logs/*.json
                    !.verify-logs/context/**
        """,
    )

    result = context_artifacts.check_context_pack_upload_policy(tmp_path, schema.MaintainerConfig())

    assert result.status == doctor_models.OK


def test_context_pack_upload_policy_allows_upload_safe_config(tmp_path: Path) -> None:
    """Packs marked non-source or non-local-only do not warn on broad upload."""

    write_workflow(
        tmp_path,
        """
        name: verify
        jobs:
          verify:
            steps:
              - uses: actions/upload-artifact@v6
                with:
                  path: ".verify-logs"
        """,
    )

    result = context_artifacts.check_context_pack_upload_policy(
        tmp_path,
        schema.MaintainerConfig(context_pack_contains_source=False),
    )

    assert result.status == doctor_models.OK


def test_context_pack_upload_path_detection_requires_upload_artifact() -> None:
    """A broad path string outside upload-artifact does not trigger warning."""

    assert not context_artifacts.workflow_uploads_broad_verify_logs("run: echo .verify-logs/\n")


def test_context_pack_upload_policy_reports_disabled_artifacts(tmp_path: Path) -> None:
    """Disabled diagnostics make context artifact upload policy inert."""

    result = context_artifacts.check_context_pack_upload_policy(
        tmp_path,
        schema.MaintainerConfig(diagnostic_artifacts_enabled=False),
    )

    assert result.status == doctor_models.OK
    assert result.state == doctor_models.DISABLED


def test_context_pack_upload_policy_reports_disabled_pack_writes(tmp_path: Path) -> None:
    """Disabled context pack writes make upload policy inert."""

    result = context_artifacts.check_context_pack_upload_policy(
        tmp_path,
        schema.MaintainerConfig(context_write_context_packs=False),
    )

    assert result.status == doctor_models.OK
    assert result.state == doctor_models.DISABLED


def test_context_pack_upload_path_detection_accepts_missing_workflows(
    tmp_path: Path,
) -> None:
    """Missing workflow directories have no unsafe upload paths."""

    assert context_artifacts.context_pack_upload_workflow_paths(tmp_path) == ()


def test_context_pack_upload_path_detection_skips_unreadable_workflows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unreadable workflow files do not crash doctor policy."""

    write_workflow(
        tmp_path,
        """
        name: verify
        jobs:
          verify:
            steps:
              - uses: actions/upload-artifact@v6
                with:
                  path: .verify-logs/
        """,
    )

    def fail_read_text(_path: Path, *args: object, **kwargs: object) -> str:
        raise OSError("cannot read")

    monkeypatch.setattr(context_artifacts.Path, "read_text", fail_read_text)

    assert context_artifacts.context_pack_upload_workflow_paths(tmp_path) == ()


def test_context_pack_upload_path_detection_handles_comments_and_quotes() -> None:
    """Quoted and commented broad verify-log paths are still unsafe."""

    workflow_text = """
    - uses: actions/upload-artifact@v6
      with:
        path: ".verify-logs" # broad upload
    """

    assert context_artifacts.workflow_uploads_broad_verify_logs(workflow_text)


def write_workflow(repo_root: Path, workflow_text: str) -> None:
    """Write a GitHub Actions workflow fixture."""

    workflow_path = repo_root / ".github" / "workflows" / "verify.yml"
    workflow_path.parent.mkdir(parents=True)
    workflow_path.write_text(workflow_text, encoding="utf-8")
