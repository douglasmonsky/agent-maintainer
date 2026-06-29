"""Tests doctor context, ratchet, and change-plan health rows."""

from __future__ import annotations

import importlib.machinery
from pathlib import Path
from types import SimpleNamespace

import pytest

from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.doctor.support import context_health, models
from agent_maintainer.ratchet.guidance import render_ratchet_guidance


def test_context_health_rows_have_stable_json_shape(tmp_path: Path) -> None:
    """Context-health doctor rows remain stable JSON objects."""

    rows = context_health.check_context_health(tmp_path, MaintainerConfig())

    assert [row.name for row in rows] == [
        "context-config",
        "context-budgets",
        "large-file-outline",
        "context-pack-directory",
        "context-pack-upload-safety",
        "ratchet-baseline",
        "ratchet-guidance",
        "change-plans",
        "compression-backend",
        "headroom-backend",
        "test-intelligence-artifacts",
    ]
    assert set(rows[0].__dict__) == {"name", "status", "message", "state", "hint"}


def test_headroom_missing_not_failure_when_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing Headroom is not a failure unless Headroom is configured."""

    monkeypatch.setattr(context_health.importlib_util, "find_spec", lambda name: None)

    result = context_health.check_headroom_backend(MaintainerConfig())

    assert result.status == models.OK
    assert result.state == models.NOT_APPLICABLE


def test_headroom_missing_fails_when_required(monkeypatch: pytest.MonkeyPatch) -> None:
    """Required configured Headroom backend fails when not installed."""

    monkeypatch.setattr(context_health.importlib_util, "find_spec", lambda name: None)
    config = MaintainerConfig(
        context_compression_backend="headroom",
        context_compression_enabled=True,
        context_compression_require_backend=True,
    )

    result = context_health.check_headroom_backend(config)

    assert result.status == models.ERROR
    assert result.state == models.MISSING
    assert "agent-maintainer[compression]" in result.hint


def test_headroom_available_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configured Headroom backend passes when import is available."""

    spec = importlib.machinery.ModuleSpec("headroom", loader=None)
    monkeypatch.setattr(context_health.importlib_util, "find_spec", lambda name: spec)
    config = MaintainerConfig(
        context_compression_backend="headroom",
        context_compression_enabled=True,
    )

    result = context_health.check_headroom_backend(config)

    assert result.status == models.OK


def test_invalid_change_plan_is_detected(tmp_path: Path) -> None:
    """Doctor reports invalid configured change plans."""

    plan_dir = tmp_path / ".agent-maintainer" / "change-plans"
    plan_dir.mkdir(parents=True)
    (plan_dir / "bad.md").write_text("not front matter\n", encoding="utf-8")

    result = context_health.check_change_plans(tmp_path, MaintainerConfig())

    assert result.status == models.ERROR
    assert result.state == models.UNSAFE_CONFIG
    assert "bad.md" in result.message


def test_stale_ratchet_guidance_is_detected(tmp_path: Path) -> None:
    """Doctor reports stale ratchet guidance."""

    config = MaintainerConfig(ratchet_enabled=True)
    (tmp_path / config.ratchet_guidance_path).write_text("stale\n", encoding="utf-8")

    result = context_health.check_ratchet_guidance(tmp_path, config)

    assert result.status == models.ERROR
    assert result.state == models.UNSAFE_CONFIG


def test_current_ratchet_guidance_passes(tmp_path: Path) -> None:
    """Doctor accepts current ratchet guidance."""

    config = MaintainerConfig(ratchet_enabled=True)
    (tmp_path / config.ratchet_guidance_path).write_text(
        render_ratchet_guidance(config),
        encoding="utf-8",
    )

    result = context_health.check_ratchet_guidance(tmp_path, config)

    assert result.status == models.OK


def test_unsafe_context_pack_upload_is_detected(tmp_path: Path) -> None:
    """Doctor reports broad verify-log artifact uploads."""

    workflow = tmp_path / ".github" / "workflows" / "verify.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        """
name: verify
jobs:
  verify:
    steps:
      - uses: actions/upload-artifact@v6
        with:
          path: .verify-logs/**
""",
        encoding="utf-8",
    )

    result = context_health.check_context_pack_upload_safety(tmp_path, MaintainerConfig())

    assert result.name == "context-pack-upload-safety"
    assert result.status == models.WARNING
    assert result.state == models.UNSAFE_CONFIG


def test_ratchet_baseline_missing_reports_state_without_failure(tmp_path: Path) -> None:
    """Missing ratchet baseline is visible but not a hard failure."""

    result = context_health.check_ratchet_baseline(
        tmp_path,
        MaintainerConfig(ratchet_enabled=True),
    )

    assert result.status == models.OK
    assert result.state == models.MISSING


def test_test_intelligence_artifacts_pass_when_coverage_exists(tmp_path: Path) -> None:
    """Coverage artifacts make test-intelligence row active."""

    log_dir = tmp_path / ".verify-logs"
    log_dir.mkdir()
    (log_dir / "coverage.json").write_text("{}", encoding="utf-8")

    result = context_health.check_test_intelligence_artifacts(
        tmp_path,
        MaintainerConfig(),
    )

    assert result.status == models.OK


def test_context_config_reports_disabled_artifacts() -> None:
    """Disabled diagnostic artifacts are explicit."""

    result = context_health.check_context_config(
        MaintainerConfig(diagnostic_artifacts_enabled=False),
    )

    assert result.status == models.OK
    assert result.state == models.DISABLED


def test_context_budgets_report_invalid_values() -> None:
    """Non-positive context budgets are unsafe config."""

    result = context_health.check_context_budgets(
        MaintainerConfig(context_hook_budget_chars=0),
    )

    assert result.status == models.ERROR
    assert result.state == models.UNSAFE_CONFIG
    assert "hook" in result.message


def test_large_file_outline_reports_disabled() -> None:
    """Disabled outline requirement is visible."""

    result = context_health.check_large_file_outline(
        MaintainerConfig(context_require_outline_for_large_files=False),
    )

    assert result.status == models.OK
    assert result.state == models.DISABLED


def test_context_pack_directory_reports_disabled_and_existing(tmp_path: Path) -> None:
    """Context pack directory row covers disabled and present states."""

    disabled = context_health.check_context_pack_directory(
        tmp_path,
        MaintainerConfig(context_write_context_packs=False),
    )
    pack_dir = tmp_path / ".verify-logs" / "context"
    pack_dir.mkdir(parents=True)
    existing = context_health.check_context_pack_directory(tmp_path, MaintainerConfig())

    assert disabled.state == models.DISABLED
    assert existing.status == models.OK
    assert existing.state == models.ACTIVE


def test_ratchet_guidance_missing_is_detected(tmp_path: Path) -> None:
    """Missing ratchet guidance fails when ratchet is enabled."""

    result = context_health.check_ratchet_guidance(
        tmp_path,
        MaintainerConfig(ratchet_enabled=True),
    )

    assert result.status == models.ERROR
    assert result.state == models.MISSING


def test_ratchet_baseline_unreadable_is_detected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unreadable ratchet baseline is unsafe config."""

    config = MaintainerConfig(ratchet_enabled=True)
    baseline_path = tmp_path / config.ratchet_baseline_path
    baseline_path.parent.mkdir(parents=True)
    baseline_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        context_health.baseline,
        "read_baseline",
        lambda path: (_ for _ in ()).throw(ValueError("bad baseline")),
    )

    result = context_health.check_ratchet_baseline(tmp_path, config)

    assert result.status == models.ERROR
    assert result.state == models.UNSAFE_CONFIG


def test_ratchet_baseline_reports_stale_and_active(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ratchet baseline row reports stale and active status."""

    config = MaintainerConfig(ratchet_enabled=True)
    baseline_path = tmp_path / config.ratchet_baseline_path
    baseline_path.parent.mkdir(parents=True)
    baseline_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(context_health.baseline, "read_baseline", lambda path: object())
    monkeypatch.setattr(
        context_health.status,
        "status_report",
        lambda baseline, base_ref: SimpleNamespace(
            stale_reasons=("base ref changed",),
            counts=lambda: {},
        ),
    )

    stale = context_health.check_ratchet_baseline(tmp_path, config)

    monkeypatch.setattr(
        context_health.status,
        "status_report",
        lambda baseline, base_ref: SimpleNamespace(
            stale_reasons=(),
            counts=lambda: {"new": 0},
        ),
    )
    active = context_health.check_ratchet_baseline(tmp_path, config)

    assert stale.status == models.WARNING
    assert stale.state == models.UNSAFE_CONFIG
    assert active.status == models.OK


def test_valid_change_plan_is_reported(tmp_path: Path) -> None:
    """Valid change plans pass doctor health."""

    plan_dir = tmp_path / ".agent-maintainer" / "change-plans"
    plan_dir.mkdir(parents=True)
    (plan_dir / "valid.md").write_text(valid_plan_text(), encoding="utf-8")

    result = context_health.check_change_plans(tmp_path, MaintainerConfig())

    assert result.status == models.OK
    assert "1 valid" in result.message


def test_enabled_large_changes_without_plans_warns(tmp_path: Path) -> None:
    """Large changes enabled without plans warns missing."""

    result = context_health.check_change_plans(
        tmp_path,
        MaintainerConfig(large_changes_enabled=True),
    )

    assert result.status == models.WARNING
    assert result.state == models.MISSING


def test_compression_backend_reports_active_and_invalid() -> None:
    """Compression backend row covers active and invalid config."""

    active = context_health.check_compression_backend(
        MaintainerConfig(
            context_compression_backend="truncate",
            context_compression_enabled=True,
        ),
    )
    invalid = context_health.check_compression_backend(
        MaintainerConfig(
            context_compression_backend="invalid",
            context_compression_enabled=True,
        ),
    )

    assert active.status == models.OK
    assert invalid.status == models.ERROR
    assert invalid.state == models.UNSAFE_CONFIG


def valid_plan_text() -> str:
    """Return valid cohesive change-plan fixture."""

    return """
+++
id = "valid-plan"
kind = "cohesive-change"
status = "active"
base_ref = "origin/main"
expires = 2099-01-01
allowed_paths = ["src/**"]
forbidden_paths = []
max_changed_files = 3
max_changed_lines = 100
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = ["src/example.py"]
+++

## Why this change intentionally large
Enough detail for validation.

## Why this should not be split smaller
Enough detail for validation.

## What allowed to change
Enough detail for validation.

## What must not change
Enough detail for validation.

## Verification plan
Enough detail for validation.

## Rollback plan
Enough detail for validation.

## Follow-up ratchet work
Enough detail for validation.
""".strip()
