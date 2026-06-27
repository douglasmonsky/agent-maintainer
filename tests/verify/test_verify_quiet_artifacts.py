"""Tests for the quiet verifier orchestration."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.models import Check, CheckResult
from agent_maintainer.verify import quiet as verify_quiet

CLI_COVERAGE_THRESHOLD = 92
CLI_INTERROGATE_THRESHOLD = 30
STRICT_COMPLEXITY = 8


def test_main_writes_artifacts_for_selected_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []
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
        verify_quiet,
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
        verify_quiet,
        "write_run_artifacts",
        lambda log_dir, context, results: calls.append((log_dir, context, results)),
    )

    assert verify_quiet.main(["--profile", "fast"]) == 0

    assert calls
    log_dir, context, results = calls[0]
    assert log_dir == Path(".verify-logs")
    assert context.profile == "fast"
    assert results[0].name == "custom"


def test_main_skips_artifacts_when_diagnostics_are_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
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
        verify_quiet,
        "run_check",
        lambda check, log_dir, max_lines, max_chars: CheckResult(check.name, passed=True),
    )
    monkeypatch.setattr(
        verify_quiet,
        "write_run_artifacts",
        lambda log_dir, context, results: pytest.fail("artifacts should be disabled"),
    )

    assert verify_quiet.main(["--profile", "fast"]) == 0
