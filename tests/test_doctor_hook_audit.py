"""Tests for doctor hook-audit diagnostics."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import guardrail_doctor_hook_audit
from scripts.guardrail_config import GuardrailConfig


def enable_codex_hooks(repo_root: Path) -> None:
    config_path = repo_root / ".codex" / "config.toml"
    config_path.parent.mkdir()
    config_path.write_text("[features]\nhooks = true\n", encoding="utf-8")


def write_hook_event(log_dir: Path, *, status: str = "passed") -> None:
    log_dir.mkdir(parents=True)
    (log_dir / guardrail_doctor_hook_audit.HOOK_AUDIT_NAME).write_text(
        json.dumps(
            {
                "timestamp": "2026-06-25T10:00:00Z",
                "hook": "PostToolUse",
                "profile": "fast",
                "status": status,
            }
        )
        + "\n",
        encoding="utf-8",
    )


def test_hook_audit_is_not_required_when_codex_hooks_are_disabled(tmp_path: Path) -> None:
    result = guardrail_doctor_hook_audit.check_hook_audit(tmp_path)

    assert result.status == guardrail_doctor_hook_audit.OK
    assert "not enabled" in result.message


def test_hook_audit_warns_when_enabled_without_records(tmp_path: Path) -> None:
    enable_codex_hooks(tmp_path)

    result = guardrail_doctor_hook_audit.check_hook_audit(
        tmp_path,
        GuardrailConfig(diagnostic_artifacts_dir=".custom-logs"),
    )

    assert result.status == guardrail_doctor_hook_audit.WARNING
    assert ".custom-logs/hooks.jsonl" in result.message


def test_hook_audit_warns_when_latest_event_is_invalid(tmp_path: Path) -> None:
    enable_codex_hooks(tmp_path)
    log_dir = tmp_path / ".verify-logs"
    log_dir.mkdir()
    (log_dir / guardrail_doctor_hook_audit.HOOK_AUDIT_NAME).write_text(
        "{not json}\n",
        encoding="utf-8",
    )

    result = guardrail_doctor_hook_audit.check_hook_audit(tmp_path)

    assert result.status == guardrail_doctor_hook_audit.WARNING
    assert "no valid events" in result.message


def test_hook_audit_warns_when_latest_event_failed(tmp_path: Path) -> None:
    enable_codex_hooks(tmp_path)
    write_hook_event(tmp_path / ".verify-logs", status="failed")

    result = guardrail_doctor_hook_audit.check_hook_audit(tmp_path)

    assert result.status == guardrail_doctor_hook_audit.WARNING
    assert "PostToolUse failed" in result.message


def test_hook_audit_passes_with_latest_passing_event(tmp_path: Path) -> None:
    enable_codex_hooks(tmp_path)
    write_hook_event(tmp_path / ".verify-logs")

    result = guardrail_doctor_hook_audit.check_hook_audit(tmp_path)

    assert result.status == guardrail_doctor_hook_audit.OK
    assert "PostToolUse passed" in result.message
