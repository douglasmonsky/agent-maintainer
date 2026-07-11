"""Tests quiet local verifier wait behavior."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from agent_maintainer.verify import async_state
from agent_maintainer.wait.models import TIMEOUT_EXIT_CODE
from agent_maintainer.wait.verifier import (
    VerifierWaitConfig,
    VerifierWaitResult,
    parse_verifier_manifest,
    query_verifier_run_once,
    render_verifier_wait_json,
    render_verifier_wait_text,
    wait_for_verifier_run,
)

ERROR_EXIT_CODE = 2
CANCELLED_PROCESS_STATUS = 143


def test_verifier_wait_renders_success_manifest(tmp_path: Path) -> None:
    """Completed passing manifest renders compact pass capsule."""
    manifest_path = write_manifest(
        tmp_path,
        "run-1",
        profile="full",
        checks=({"name": "ruff", "status": "passed"},),
    )

    result = wait_for_verifier_run(VerifierWaitConfig(run_id="run-1", log_dir=tmp_path))

    assert result.exit_code == 0
    assert parse_verifier_manifest(manifest_path).succeeded
    assert render_verifier_wait_text(result) == (
        "Result: PASS\n"
        "Profile: full\n"
        "Run ID: run-1\n"
        "Duration: 2.5s\n"
        "Expected duration: expected test run"
    )


def test_verifier_wait_treats_warning_checks_as_success(tmp_path: Path) -> None:
    """Warning-only verifier manifests are successful waits."""

    manifest_path = write_manifest(
        tmp_path,
        "run-warning",
        profile="precommit",
        checks=(
            {"name": "ruff", "status": "passed"},
            {"name": "change-budget", "status": "warning"},
        ),
    )

    result = wait_for_verifier_run(
        VerifierWaitConfig(run_id="run-warning", log_dir=tmp_path),
    )
    payload = json.loads(render_verifier_wait_json(result))

    assert result.exit_code == 0
    assert parse_verifier_manifest(manifest_path).succeeded
    assert payload["status"] == "passed"
    assert payload["failed_checks"] == []
    assert "Result: PASS" in render_verifier_wait_text(result)


def test_verifier_wait_renders_failure_capsule(tmp_path: Path) -> None:
    """Failed manifest renders facts and expansion commands, not log content."""
    write_manifest(
        tmp_path,
        "run-2",
        profile="precommit",
        failure_snapshot=".verify-logs/runs/run-2/LAST_FAILURE.md",
        checks=(
            {"name": "ruff", "status": "passed"},
            {
                "name": "pyright",
                "status": "failed",
                "log_path": ".verify-logs/runs/run-2/pyright.log",
                "expansion_commands": (
                    "python -m agent_maintainer context --log-dir "
                    ".verify-logs/runs/run-2 failures --check pyright --limit 20",
                ),
            },
        ),
    )

    result = wait_for_verifier_run(VerifierWaitConfig(run_id="run-2", log_dir=tmp_path))
    text = render_verifier_wait_text(result)

    assert result.exit_code == 1
    assert "Result: FAIL\nProfile: precommit\nRun ID: run-2" in text
    assert "1. pyright: failed (.verify-logs/runs/run-2/pyright.log)" in text
    assert "Likely next action:\npython -m agent_maintainer context" in text
    assert "Expand only if needed:\n.verify-logs/runs/run-2/LAST_FAILURE.md" in text


def test_verifier_wait_times_out_without_manifest(tmp_path: Path) -> None:
    """Missing manifest times out with a reusable wait command."""
    ticks = iter((0, 2))

    result = wait_for_verifier_run(
        VerifierWaitConfig(
            run_id="missing",
            log_dir=tmp_path,
            interval_seconds=1,
            timeout_seconds=1,
        ),
        sleep=lambda _seconds: None,
        monotonic=lambda: next(ticks),
    )

    assert result.exit_code == TIMEOUT_EXIT_CODE
    assert "Result: TIMEOUT" in render_verifier_wait_text(result)


def test_verifier_wait_reads_cached_pass_job(tmp_path: Path) -> None:
    """Cached verifier pass stdout is terminal without run manifest."""

    write_cached_job(tmp_path, "cached-pass", profile="ci", outcome="PASS")

    result = wait_for_verifier_run(VerifierWaitConfig(run_id="cached-pass", log_dir=tmp_path))
    payload = json.loads(render_verifier_wait_json(result))

    assert result.exit_code == 0
    assert payload["status"] == "passed"
    assert "Expected duration: cached verifier result" in render_verifier_wait_text(result)


def test_verifier_query_once_reads_cached_fail_job(tmp_path: Path) -> None:
    """Background sweeps treat cached verifier failures as terminal."""

    write_cached_job(tmp_path, "cached-fail", profile="ci", outcome="FAIL")

    result = query_verifier_run_once(
        VerifierWaitConfig(run_id="cached-fail", log_dir=tmp_path),
    )

    assert result is not None
    assert result.exit_code == 1
    assert "Result: FAIL" in render_verifier_wait_text(result)


def test_cached_job_with_non_object_metadata_uses_empty_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed cached metadata does not hide a terminal verifier outcome."""

    write_cached_job(tmp_path, "cached-pass", profile="ci", outcome="PASS")
    (tmp_path / "jobs" / "cached-pass.json").write_text("[]", encoding="utf-8")

    def missing_async_state(_path: Path) -> None:
        return None

    monkeypatch.setattr(async_state, "read_async_state", missing_async_state)

    result = query_verifier_run_once(
        VerifierWaitConfig(run_id="cached-pass", log_dir=tmp_path),
    )

    assert result is not None
    assert result.manifest is not None
    assert result.manifest.profile == ""


def test_verifier_wait_distinguishes_quality_failure_state(tmp_path: Path) -> None:
    """A completed nonzero verifier is a quality failure, not infrastructure error."""

    write_lifecycle_state(tmp_path, "quality-fail", status=async_state.JOB_STATUS_FAILED)

    result = query_verifier_run_once(
        VerifierWaitConfig(run_id="quality-fail", log_dir=tmp_path),
    )

    assert result is not None
    assert result.exit_code == 1
    assert result.error == ""
    assert "Result: FAIL" in render_verifier_wait_text(result)


def test_verifier_wait_reports_infrastructure_error_state(tmp_path: Path) -> None:
    """A child crash becomes terminal ERROR instead of a misleading timeout."""

    write_lifecycle_state(
        tmp_path,
        "infra-error",
        status=async_state.JOB_STATUS_ERROR,
        error="RuntimeError: child crashed",
    )

    result = query_verifier_run_once(
        VerifierWaitConfig(run_id="infra-error", log_dir=tmp_path),
    )

    assert result is not None
    assert result.exit_code == ERROR_EXIT_CODE
    assert result.process_exit_code == 1
    assert "Result: ERROR" in render_verifier_wait_text(result)
    assert "child crashed" in render_verifier_wait_text(result)


def test_verifier_wait_reports_cancelled_state(tmp_path: Path) -> None:
    """Signal cancellation has a distinct terminal result and exit status."""

    write_lifecycle_state(
        tmp_path,
        "cancelled",
        status=async_state.JOB_STATUS_CANCELLED,
        error="received signal SIGTERM",
        exit_code=CANCELLED_PROCESS_STATUS,
    )

    result = query_verifier_run_once(
        VerifierWaitConfig(run_id="cancelled", log_dir=tmp_path),
    )

    assert result is not None
    assert result.cancelled is True
    assert result.exit_code == CANCELLED_PROCESS_STATUS
    assert result.process_exit_code == CANCELLED_PROCESS_STATUS
    assert "Result: CANCELLED" in render_verifier_wait_text(result)
    assert json.loads(render_verifier_wait_json(result))["status"] == "cancelled"


def test_current_job_state_rejects_same_run_stale_manifest(tmp_path: Path) -> None:
    """A reused run id cannot let an old PASS override current lifecycle state."""

    manifest_path = write_manifest(
        tmp_path,
        "reused-run",
        profile="full",
        checks=({"name": "stale-check", "status": "passed"},),
    )
    os.utime(manifest_path, (1, 1))
    write_lifecycle_state(
        tmp_path,
        "reused-run",
        status=async_state.JOB_STATUS_RUNNING,
        exit_code=None,
    )

    pending = query_verifier_run_once(
        VerifierWaitConfig(run_id="reused-run", log_dir=tmp_path),
    )

    assert pending is None
    write_lifecycle_state(
        tmp_path,
        "reused-run",
        status=async_state.JOB_STATUS_FAILED,
    )
    terminal = query_verifier_run_once(
        VerifierWaitConfig(run_id="reused-run", log_dir=tmp_path),
    )
    assert terminal is not None
    assert terminal.exit_code == 1
    assert terminal.manifest is not None
    assert [check.name for check in terminal.manifest.checks] == ["verifier"]


def test_verifier_wait_json_lists_failed_checks(tmp_path: Path) -> None:
    """JSON output exposes machine-readable failed check names."""
    write_manifest(
        tmp_path,
        "run-3",
        profile="ci",
        checks=({"name": "change-budget", "status": "failed"},),
    )

    result = wait_for_verifier_run(VerifierWaitConfig(run_id="run-3", log_dir=tmp_path))
    payload = json.loads(render_verifier_wait_json(result))

    assert payload["exit_code"] == 1
    assert payload["profile"] == "ci"
    assert payload["failed_checks"] == ["change-budget"]


def test_verifier_wait_reports_invalid_manifest(tmp_path: Path) -> None:
    """Invalid manifest content becomes compact error output."""
    run_dir = tmp_path / "runs" / "bad"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text("[]", encoding="utf-8")

    result = wait_for_verifier_run(VerifierWaitConfig(run_id="bad", log_dir=tmp_path))
    text = render_verifier_wait_text(result)

    assert result.exit_code == ERROR_EXIT_CODE
    assert "Result: ERROR" in text
    assert "python -m agent_maintainer wait verifier bad" in text


def test_verifier_unknown_result_exits_nonzero() -> None:
    """Missing manifest result renders unknown capsule."""
    result = VerifierWaitResult(run_id="unknown", manifest=None)
    text = render_verifier_wait_text(result)

    assert result.exit_code == 1
    assert "UNKNOWN" in text


def test_verifier_manifest_handles_sparse_fields(tmp_path: Path) -> None:
    """Sparse manifest fields use safe defaults."""
    run_dir = tmp_path / "runs" / "sparse"
    run_dir.mkdir(parents=True)
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "checks": "not-a-list",
                "timing": {},
            },
        ),
        encoding="utf-8",
    )

    manifest = parse_verifier_manifest(manifest_path)

    assert manifest.run_id == "sparse"
    assert manifest.checks == ()
    assert manifest.duration_seconds is None


def test_verifier_duration_renders_minutes(tmp_path: Path) -> None:
    """Minute-scale durations render compactly."""
    manifest_path = write_manifest(
        tmp_path,
        "run-4",
        profile="manual",
        checks=({"name": "mutmut", "status": "passed"},),
    )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["timing"]["duration_seconds"] = 65
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    result = wait_for_verifier_run(VerifierWaitConfig(run_id="run-4", log_dir=tmp_path))

    assert "Duration: 1m 5s" in render_verifier_wait_text(result)


def write_cached_job(
    log_dir: Path,
    run_id: str,
    *,
    profile: str,
    outcome: str,
) -> None:
    """Write cached verifier job output."""

    jobs_dir = log_dir / "jobs"
    jobs_dir.mkdir(parents=True)
    (jobs_dir / f"{run_id}.json").write_text(
        json.dumps({"profile": profile, "run_id": run_id}),
        encoding="utf-8",
    )
    (jobs_dir / f"{run_id}.stdout.log").write_text(outcome, encoding="utf-8")


def write_lifecycle_state(
    log_dir: Path,
    run_id: str,
    *,
    status: str,
    error: str = "",
    exit_code: int | None = 1,
) -> None:
    """Write one terminal detached-verifier lifecycle record."""

    jobs_dir = log_dir / "jobs"
    now = time.time()
    async_state.write_async_state(
        jobs_dir / f"{run_id}.json",
        async_state.AsyncVerifierState(
            run_id=run_id,
            profile="full",
            status=status,
            process_id=123,
            command=("python", "-m", "agent_maintainer.verify.async_child"),
            fingerprint={"profile": "full"},
            stdout_path=str(jobs_dir / f"{run_id}.stdout.log"),
            stderr_path=str(jobs_dir / f"{run_id}.stderr.log"),
            started_at=now,
            updated_at=now,
            exit_code=exit_code,
            error=error,
            phase="verify",
        ),
    )


def write_manifest(
    log_dir: Path,
    run_id: str,
    *,
    profile: str,
    checks: tuple[dict[str, object], ...],
    failure_snapshot: str = "",
) -> Path:
    """Write a minimal verifier run manifest."""
    run_dir = log_dir / "runs" / run_id
    run_dir.mkdir(parents=True)
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "profile": profile,
                "run_id": run_id,
                "checks": checks,
                "expected_duration_hint": "expected test run",
                "failure_snapshot": failure_snapshot,
                "timing": {"duration_seconds": 2.5},
            },
        ),
        encoding="utf-8",
    )
    return manifest_path
