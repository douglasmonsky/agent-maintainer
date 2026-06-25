"""Tests for doctor verification-log diagnostics."""

from __future__ import annotations

import json
import os
from pathlib import Path

from scripts import guardrail_doctor_logs


def write_verification_manifest(
    log_dir: Path,
    *,
    status: str = "passed",
    artifacts: tuple[str, ...] = (),
) -> Path:
    """Write a minimal verifier manifest for doctor tests."""

    manifest = log_dir / guardrail_doctor_logs.MANIFEST_NAME
    manifest.write_text(
        json.dumps(
            {
                "generated_at": "2026-06-25T10:00:00Z",
                "profile": "full",
                "checks": [
                    {
                        "name": "ruff",
                        "status": status,
                        "log_path": ".verify-logs/ruff.log",
                        "artifacts": list(artifacts),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return manifest


def test_recent_logs_warn_and_pass(tmp_path: Path) -> None:
    assert guardrail_doctor_logs.check_recent_logs(tmp_path).status == guardrail_doctor_logs.WARNING

    log_dir = tmp_path / ".verify-logs"
    log_dir.mkdir()

    assert guardrail_doctor_logs.check_recent_logs(tmp_path).status == guardrail_doctor_logs.WARNING

    (log_dir / "ruff.log").write_text("ok\n", encoding="utf-8")

    assert guardrail_doctor_logs.check_recent_logs(tmp_path).status == guardrail_doctor_logs.WARNING

    write_verification_manifest(log_dir)

    result = guardrail_doctor_logs.check_recent_logs(tmp_path)

    assert result.status == guardrail_doctor_logs.OK
    assert "ruff.log" in result.message


def test_recent_logs_warn_when_manifest_is_stale(tmp_path: Path) -> None:
    log_dir = tmp_path / ".verify-logs"
    log_dir.mkdir()
    log_path = log_dir / "ruff.log"
    log_path.write_text("ok\n", encoding="utf-8")
    manifest = write_verification_manifest(log_dir)
    os.utime(manifest, (10, 10))
    os.utime(log_path, (20, 20))

    result = guardrail_doctor_logs.check_recent_logs(tmp_path)

    assert result.status == guardrail_doctor_logs.WARNING
    assert "older" in result.message


def test_recent_logs_warn_when_manifest_references_missing_artifact(tmp_path: Path) -> None:
    log_dir = tmp_path / ".verify-logs"
    log_dir.mkdir()
    (log_dir / "ruff.log").write_text("ok\n", encoding="utf-8")
    write_verification_manifest(log_dir, artifacts=("missing.json",))

    result = guardrail_doctor_logs.check_recent_logs(tmp_path)

    assert result.status == guardrail_doctor_logs.WARNING
    assert "artifact is missing" in result.message


def test_recent_logs_warn_when_failure_note_is_missing_or_stale(tmp_path: Path) -> None:
    log_dir = tmp_path / ".verify-logs"
    log_dir.mkdir()
    (log_dir / "ruff.log").write_text("failed\n", encoding="utf-8")
    write_verification_manifest(log_dir, status="failed")

    missing_note = guardrail_doctor_logs.check_recent_logs(tmp_path)

    assert missing_note.status == guardrail_doctor_logs.WARNING
    assert "LAST_FAILURE.md is absent" in missing_note.message

    (log_dir / guardrail_doctor_logs.LAST_FAILURE_NAME).write_text(
        "failure\n",
        encoding="utf-8",
    )
    write_verification_manifest(log_dir, status="passed")

    stale_note = guardrail_doctor_logs.check_recent_logs(tmp_path)

    assert stale_note.status == guardrail_doctor_logs.WARNING
    assert "LAST_FAILURE.md is stale" in stale_note.message
