"""Tests for the quiet verifier orchestration."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.models import Check, CheckResult
from agent_maintainer.verify import quiet as verify_quiet
from agent_maintainer.verify import run_steps as verify_run_steps
from agent_maintainer.verify.async_jobs import AsyncVerifierLaunch, AsyncVerifierRequest
from agent_maintainer.verify.result_summary import apply_optional_skip_policy

CLI_COVERAGE_THRESHOLD = 92
CLI_INTERROGATE_THRESHOLD = 30
STRICT_COMPLEXITY = 8


def test_main_async_launches_background_verifier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Async verifier prints wait command without running checks inline."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        verify_quiet,
        "load_config",
        lambda: replace(
            MaintainerConfig(),
            source_roots=("src",),
            package_paths=("src",),
            test_roots=("tests",),
            diagnostic_artifacts_dir=str(tmp_path / ".verify-logs"),
        ),
    )
    monkeypatch.setattr(
        verify_quiet.async_jobs,
        "launch_async_verifier",
        fake_async_launch,
    )

    status = verify_quiet.main(["--profile", "fast", "--async"])

    assert status == 0
    output = capsys.readouterr().out
    assert "Result: PENDING" in output
    assert "python -m agent_maintainer wait verifier async-run" in output


def test_collect_results_stops_on_layout_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    args = verify_quiet.parse_args(["--profile", "precommit"])
    config = replace(MaintainerConfig(), source_roots=("missing",), package_paths=("missing",))

    results = verify_run_steps.collect_results(args, config, [])

    assert results[0].name == "maintainer-layout"
    assert results[0].passed is False


def test_collect_results_stops_on_invalid_git_refs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Invalid verifier refs fail before running selected checks."""

    monkeypatch.chdir(tmp_path)
    args = verify_quiet.parse_args(["--profile", "ci"])
    config = MaintainerConfig()
    monkeypatch.setattr(
        verify_run_steps,
        "layout_failures",
        lambda _config, _profile: [],
    )
    monkeypatch.setattr(
        verify_run_steps,
        "ref_failures",
        lambda *_args, **_kwargs: ("--base-ref 'missing' is not valid commit ref.",),
    )

    def fail_run_check(*_args: object, **_kwargs: object) -> CheckResult:
        pytest.fail("checks should not run when refs are invalid")

    monkeypatch.setattr(verify_run_steps, "run_check", fail_run_check)

    results = verify_quiet.collect_results(args, config, [Check("tool", ["tool"], frozenset())])

    assert results[0].name == "git-ref-validation"
    assert results[0].passed is False
    assert "--base-ref 'missing'" in results[0].output


def test_optional_skip_policy_can_fail_skips() -> None:
    results = [
        CheckResult(
            "pip-audit",
            passed=True,
            output="disabled",
            skipped=True,
            command=("pip-audit",),
            log_path=".verify-logs/pip-audit.log",
        )
    ]

    converted = apply_optional_skip_policy(results, fail_on_optional_skip=True)

    assert converted[0].passed is False
    assert converted[0].output == "optional check skipped: disabled"
    assert converted[0].skipped is False
    assert converted[0].command == ("pip-audit",)
    assert converted[0].log_path == ".verify-logs/pip-audit.log"


def test_main_prints_success_with_warning_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "scripts").mkdir()
    monkeypatch.setattr(
        verify_quiet,
        "load_config",
        lambda: replace(
            MaintainerConfig(),
            source_roots=("scripts",),
            package_paths=("scripts",),
            require_tests=False,
        ),
    )
    monkeypatch.setattr(
        verify_quiet,
        "make_checks",
        lambda config, base_ref, compare_branch, staged=False: [
            Check("change-budget", ["true"], frozenset(("fast",)))
        ],
    )
    monkeypatch.setattr(
        verify_run_steps,
        "run_check",
        lambda check, log_dir, max_lines, max_chars: CheckResult(
            check.name,
            passed=True,
            output="WARN: source changed without tests",
            warning=True,
        ),
    )

    assert verify_quiet.main(["--profile", "fast"]) == 0

    output = capsys.readouterr().out
    assert "PASS" in output
    assert "WARNINGS:" in output
    assert "change-budget: WARN: source changed without tests" in output


def test_main_prints_success_for_passing_selected_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "scripts").mkdir()

    monkeypatch.setattr(
        verify_quiet,
        "load_config",
        lambda: replace(
            MaintainerConfig(),
            source_roots=("scripts",),
            package_paths=("scripts",),
            require_tests=False,
        ),
    )
    monkeypatch.setattr(
        verify_quiet,
        "make_checks",
        lambda config, base_ref, compare_branch, staged=False: [
            Check("custom", ["true"], frozenset(("fast",)))
        ],
    )
    monkeypatch.setattr(
        verify_run_steps,
        "run_check",
        lambda check, log_dir, max_lines, max_chars: CheckResult(
            check.name,
            passed=True,
            exit_code=0,
        ),
    )

    assert verify_quiet.main(["--profile", "fast"]) == 0
    output = capsys.readouterr().out
    assert "PASS" in output
    assert "Profile: fast" in output
    assert "Duration: unknown (expected quick edit check)" in output


def test_main_writes_runtime_profile_events_when_enabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Enabled runtime events record profile lifecycle without noisy output."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "scripts").mkdir()
    event_dir = tmp_path / ".events"
    monkeypatch.setattr(
        verify_quiet,
        "load_config",
        lambda: replace(
            MaintainerConfig(),
            source_roots=("scripts",),
            package_paths=("scripts",),
            require_tests=False,
            runtime_events_enabled=True,
            runtime_events_dir=str(event_dir),
        ),
    )
    monkeypatch.setattr(
        verify_quiet,
        "make_checks",
        lambda config, base_ref, compare_branch, staged=False: [
            Check("custom", ["true"], frozenset(("fast",)))
        ],
    )
    monkeypatch.setattr(
        verify_run_steps,
        "run_check",
        lambda check, log_dir, max_lines, max_chars: CheckResult(
            check.name,
            passed=True,
            exit_code=0,
        ),
    )

    assert verify_quiet.main(["--profile", "fast"]) == 0

    output = capsys.readouterr().out
    assert "PASS" in output
    assert ".events" not in output
    event_files = tuple(event_dir.glob("*.jsonl"))
    assert len(event_files) == 1
    records = [json.loads(line) for line in event_files[0].read_text(encoding="utf-8").splitlines()]
    assert [record["event_name"] for record in records] == [
        "profile.started",
        "verifier.fresh",
        "checks.selected",
        "check.started",
        "check.finished",
        "artifact.written",
        "artifact.written",
        "artifact.written",
        "profile.finished",
    ]
    check_record = next(record for record in records if record["event_name"] == "check.finished")
    assert records[0]["profile"] == "fast"
    assert check_record["check"] == "custom"
    assert check_record["status"] == "pass"
    assert check_record["exit_code"] == 0


def fake_async_launch(_request: AsyncVerifierRequest) -> AsyncVerifierLaunch:
    """Return deterministic async launch for verifier CLI tests."""
    return AsyncVerifierLaunch(
        run_id="async-run",
        profile="fast",
        state_path=Path(".verify-logs/jobs/async-run.json"),
        process_id=1234,
        command=("python", "-m", "agent_maintainer", "verify"),
    )
