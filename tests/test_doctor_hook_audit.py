"""Tests for doctor hook-audit diagnostics."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from scripts import guardrail_doctor_hook_audit
from scripts.guardrail_config import GuardrailConfig


def enable_codex_hooks(repo_root: Path) -> None:
    config_path = repo_root / ".codex" / "config.toml"
    config_path.parent.mkdir()
    config_path.write_text("[features]\nhooks = true\n", encoding="utf-8")


def write_hook_event(
    log_dir: Path, *, status: str = "passed", timestamp: str = "2026-06-25T10:00:00Z"
) -> None:
    log_dir.mkdir(parents=True)
    (log_dir / guardrail_doctor_hook_audit.HOOK_AUDIT_NAME).write_text(
        json.dumps(
            {
                "timestamp": timestamp,
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


def test_valid_hook_events_reports_unreadable_audit_path(tmp_path: Path) -> None:
    events, malformed_count = guardrail_doctor_hook_audit.valid_hook_events(tmp_path)

    assert events == []
    assert malformed_count == 1


def test_hook_audit_warns_when_latest_event_has_invalid_timestamp(tmp_path: Path) -> None:
    enable_codex_hooks(tmp_path)
    log_dir = tmp_path / ".verify-logs"
    write_hook_event(log_dir, timestamp="not-a-time")

    result = guardrail_doctor_hook_audit.check_hook_audit(tmp_path)

    assert result.status == guardrail_doctor_hook_audit.WARNING
    assert "no valid events" in result.message
    assert "malformed=1" in result.message


def test_hook_audit_warns_when_latest_event_is_stale(tmp_path: Path) -> None:
    enable_codex_hooks(tmp_path)
    write_hook_event(tmp_path / ".verify-logs")

    result = guardrail_doctor_hook_audit.check_hook_audit(
        tmp_path,
        now=datetime(2026, 6, 28, 10, tzinfo=UTC),
    )

    assert result.status == guardrail_doctor_hook_audit.WARNING
    assert "stale" in result.message


def test_hook_audit_reports_recent_valid_event_with_malformed_count(
    tmp_path: Path,
) -> None:
    enable_codex_hooks(tmp_path)
    log_dir = tmp_path / ".verify-logs"
    log_dir.mkdir()
    audit_path = log_dir / guardrail_doctor_hook_audit.HOOK_AUDIT_NAME
    audit_path.write_text(
        "\n"
        "[]\n"
        "{bad json}\n"
        + json.dumps(
            {
                "timestamp": "2026-06-25T10:00:00Z",
                "hook": "Stop",
                "profile": "precommit",
                "status": "passed",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = guardrail_doctor_hook_audit.check_hook_audit(
        tmp_path,
        now=datetime(2026, 6, 25, 11, tzinfo=UTC),
    )

    assert result.status == guardrail_doctor_hook_audit.OK
    assert "ignored malformed=2" in result.message


def test_event_timestamp_rejects_non_string_timestamp() -> None:
    event = {"timestamp": object(), "hook": "Stop", "profile": "precommit", "status": "passed"}

    assert guardrail_doctor_hook_audit.event_timestamp(event) is None


def test_event_timestamp_accepts_naive_timestamp() -> None:
    event = {
        "timestamp": "2026-06-25T10:00:00",
        "hook": "Stop",
        "profile": "precommit",
        "status": "passed",
    }

    parsed = guardrail_doctor_hook_audit.event_timestamp(event)

    assert parsed is not None
    assert parsed.tzinfo is UTC


def test_no_valid_events_result_without_malformed_count() -> None:
    result = guardrail_doctor_hook_audit.no_valid_events_result(0)

    assert result.status == guardrail_doctor_hook_audit.WARNING
    assert "malformed" not in result.message


def test_hook_audit_result_defensively_handles_invalid_event_timestamp() -> None:
    event = {"timestamp": object(), "hook": "Stop", "profile": "precommit", "status": "passed"}

    result = guardrail_doctor_hook_audit.hook_audit_result(event)

    assert result.status == guardrail_doctor_hook_audit.WARNING
    assert "malformed=1" in result.message


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
