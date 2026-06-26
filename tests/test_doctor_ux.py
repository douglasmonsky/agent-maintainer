"""Tests richer doctor UX states and summaries."""

from __future__ import annotations

import json
from pathlib import Path

from guardrail_lib.verify.artifacts import MANIFEST_NAME
from scripts import (
    guardrail_doctor,
    guardrail_doctor_logs,
    guardrail_doctor_models,
    guardrail_doctor_policy,
    guardrail_doctor_setup,
)
from scripts.guardrail_config import GuardrailConfig


def test_architecture_backend_reports_active_tach(tmp_path: Path) -> None:
    (tmp_path / "tach.toml").write_text(
        'source_roots = ["scripts"]\nroot_module = "forbid"\n',
        encoding="utf-8",
    )
    config = GuardrailConfig(architecture_tool="tach")

    result = guardrail_doctor_setup.check_architecture_backend(tmp_path, config)

    assert result.status == guardrail_doctor.OK
    assert result.state == guardrail_doctor_models.ACTIVE
    assert "tach active" in result.message


def test_architecture_backend_reports_missing_config(tmp_path: Path) -> None:
    config = GuardrailConfig(architecture_tool="tach")

    result = guardrail_doctor_setup.check_architecture_backend(tmp_path, config)

    assert result.status == guardrail_doctor.WARNING
    assert result.state == guardrail_doctor_models.MISSING
    assert "tach.toml" in result.message
    assert result.hint


def test_thresholds_report_active_enforcement_values() -> None:
    config = GuardrailConfig(
        coverage_fail_under=87,
        diff_cover_fail_under=93,
        interrogate_fail_under=81,
        ruff_max_complexity=7,
        file_length_max_physical=500,
        file_length_max_source=375,
        xenon_max_absolute="A",
        xenon_max_modules="A",
        xenon_max_average="A",
    )

    result = guardrail_doctor_setup.check_thresholds(config)

    assert result.status == guardrail_doctor.OK
    assert result.state == guardrail_doctor_models.ACTIVE
    assert "coverage=87%" in result.message
    assert "diff-cover=93%" in result.message
    assert "interrogate=81%" in result.message
    assert "ruff-complexity=7" in result.message
    assert "xenon=A/A/A" in result.message
    assert "file-length=500 physical/375 source" in result.message


def test_structure_thresholds_report_paths_and_ignored_globs() -> None:
    config = GuardrailConfig(
        mode="fresh-strict",
        source_roots=("scripts",),
        folder_file_warn=12,
        folder_file_block=34,
        structure_cluster_min=3,
        structure_ignore_paths=("tests/**", "generated/**"),
    )

    result = guardrail_doctor_setup.check_structure_thresholds(config)

    assert result.status == guardrail_doctor.OK
    assert result.state == guardrail_doctor_models.ACTIVE
    assert "paths=scripts" in result.message
    assert "warn=12" in result.message
    assert "block=34" in result.message
    assert "cluster-min=3" in result.message
    assert "tests/**" in result.message


def test_verification_logs_report_removed_check_drift(tmp_path: Path) -> None:
    log_dir = tmp_path / ".verify-logs"
    log_dir.mkdir()
    latest_log = log_dir / "removed-check.log"
    latest_log.write_text("old\n", encoding="utf-8")
    manifest = {
        "generated_at": "2026-06-26T00:00:00Z",
        "profile": "full",
        "checks": [{"name": "removed-check", "status": "passed"}],
    }
    (log_dir / MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")

    result = guardrail_doctor_logs.check_recent_logs(tmp_path, GuardrailConfig())

    assert result.status == guardrail_doctor.WARNING
    assert result.state == guardrail_doctor_models.UNSAFE_CONFIG
    assert "disabled or removed" in result.message
    assert result.hint


def test_pre_commit_absent_config_is_not_applicable(tmp_path: Path) -> None:
    result = guardrail_doctor.check_pre_commit(tmp_path)

    assert result.status == guardrail_doctor.WARNING
    assert result.state == guardrail_doctor_models.NOT_APPLICABLE


def test_verification_logs_report_disabled_artifacts(tmp_path: Path) -> None:
    config = GuardrailConfig(diagnostic_artifacts_enabled=False)

    result = guardrail_doctor_logs.check_recent_logs(tmp_path, config)

    assert result.status == guardrail_doctor.OK
    assert result.state == guardrail_doctor_models.DISABLED


def test_verification_logs_report_invalid_manifest_json(tmp_path: Path) -> None:
    log_dir = tmp_path / ".verify-logs"
    log_dir.mkdir()
    (log_dir / "ruff.log").write_text("ok\n", encoding="utf-8")
    (log_dir / MANIFEST_NAME).write_text("{not-json", encoding="utf-8")

    result = guardrail_doctor_logs.check_recent_logs(tmp_path, GuardrailConfig())

    assert result.status == guardrail_doctor.WARNING
    assert result.state == guardrail_doctor_models.UNSAFE_CONFIG
    assert result.hint


def test_verification_log_catalog_drift_ignores_current_checks() -> None:
    payload = {"checks": [{"name": "ruff"}]}

    assert guardrail_doctor_logs.catalog_drift_issues(GuardrailConfig(), payload) == []


def test_pyright_invalid_json_is_unsafe_config(tmp_path: Path) -> None:
    (tmp_path / "pyrightconfig.json").write_text("{not-json", encoding="utf-8")

    result = guardrail_doctor_policy.check_pyright_config(tmp_path, GuardrailConfig())

    assert result.status == guardrail_doctor.WARNING
    assert result.state == guardrail_doctor_models.UNSAFE_CONFIG
    assert result.hint


def test_pip_audit_disabled_state_is_explicit() -> None:
    result = guardrail_doctor_policy.check_pip_audit_safety(GuardrailConfig(enable_pip_audit=False))

    assert result.status == guardrail_doctor.OK
    assert result.state == guardrail_doctor_models.DISABLED
