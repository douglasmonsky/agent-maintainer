"""Tests quiet local verifier wait behavior."""

from __future__ import annotations

import json
from pathlib import Path

from agent_maintainer.wait.models import TIMEOUT_EXIT_CODE
from agent_maintainer.wait.verifier import (
    VerifierWaitConfig,
    parse_verifier_manifest,
    render_verifier_wait_json,
    render_verifier_wait_text,
    wait_for_verifier_run,
)


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
