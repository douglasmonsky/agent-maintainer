"""Tests for the quiet verifier orchestration."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.models import Check, CheckResult
from agent_maintainer.verify import quiet as verify_quiet
from agent_maintainer.verify import run_steps as verify_run_steps

CLI_COVERAGE_THRESHOLD = 92
CLI_INTERROGATE_THRESHOLD = 30
STRICT_COMPLEXITY = 8


def test_main_writes_artifacts_for_selected_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []
    configured_artifact_dirs: list[str] = []
    monkeypatch.chdir(tmp_path)
    allow_foreground_verify(monkeypatch)
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

    def fake_make_checks(
        config: MaintainerConfig,
        _base_ref: str,
        _compare_branch: str,
        *,
        staged: bool = False,
    ) -> list[Check]:
        assert staged is False
        configured_artifact_dirs.append(config.diagnostic_artifacts_dir)
        return [Check("custom", ["true"], frozenset(("fast",)))]

    monkeypatch.setattr(verify_quiet, "make_checks", fake_make_checks)
    monkeypatch.setattr(
        verify_run_steps,
        "run_check",
        lambda check, log_dir, max_lines, max_chars: CheckResult(
            check.name,
            passed=True,
            command=tuple(check.command),
            exit_code=0,
            log_path=str(log_dir / f"{check.name}.log"),
        ),
    )
    monkeypatch.setattr(
        verify_run_steps,
        "write_run_artifacts",
        lambda log_dir, context, results, **_kwargs: calls.append(
            (log_dir, context, results),
        ),
    )

    assert verify_quiet.main(["--profile", "fast"]) == 0

    assert calls
    log_dir, context, results = calls[0]
    assert log_dir == Path(".verify-logs")
    assert context.profile == "fast"
    assert context.run_id
    expected_run_dir = Path(".verify-logs") / "runs" / context.run_id
    assert configured_artifact_dirs == [str(expected_run_dir)]
    assert results[0].name == "custom"
    assert results[0].log_path == str(expected_run_dir / "custom.log")


def test_failed_run_prints_snapshot_scoped_context_commands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    allow_foreground_verify(monkeypatch)
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
            Check("custom", ["false"], frozenset(("fast",)))
        ],
    )
    monkeypatch.setattr(
        verify_run_steps,
        "run_check",
        lambda check, log_dir, max_lines, max_chars: CheckResult(
            check.name,
            passed=False,
            output="custom failed",
            command=tuple(check.command),
            exit_code=1,
            log_path=str(log_dir / f"{check.name}.log"),
        ),
    )

    assert verify_quiet.main(["--profile", "fast"]) == 1

    output = capsys.readouterr().out
    assert output.startswith("Result: FAIL\nProfile: fast\nRun ID:")
    assert "Top repair facts:\n1. custom: custom failed" in output
    assert "Likely next action:\nfalse" in output
    assert "Expand only if needed:" in output
    assert "python -m agent_maintainer context --log-dir .verify-logs/runs/" in output
    assert "failures --check custom --limit 20" in output
    assert "log custom --tail 120" not in output


def test_main_skips_artifacts_when_diagnostics_are_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    allow_foreground_verify(monkeypatch)
    (tmp_path / "scripts").mkdir()
    monkeypatch.setattr(
        verify_quiet,
        "load_config",
        lambda: replace(
            MaintainerConfig(),
            source_roots=("scripts",),
            package_paths=("scripts",),
            require_tests=False,
            diagnostic_artifacts_enabled=False,
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
        lambda check, log_dir, max_lines, max_chars: CheckResult(check.name, passed=True),
    )
    monkeypatch.setattr(
        verify_run_steps,
        "write_run_artifacts",
        lambda log_dir, context, results: pytest.fail("artifacts should be disabled"),
    )

    assert verify_quiet.main(["--profile", "fast"]) == 0


def allow_foreground_verify(monkeypatch: pytest.MonkeyPatch) -> None:
    """Allow foreground verifier execution in tests with inherited Codex env."""

    monkeypatch.setenv("AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT", "1")
