"""Tests Codex verifier background wait enforcement."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.models import Check, CheckResult
from agent_maintainer.verify import quiet as verify_quiet
from agent_maintainer.verify import run_steps as verify_run_steps
from agent_maintainer.verify.async_jobs import AsyncVerifierLaunch, AsyncVerifierRequest
from tests.support.callbacks import constant_callback, forbidden_callback


def test_codex_main_registers_background_verifier_wait(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Codex foreground verify converts to async background wait."""

    seen_waits: list[tuple[str, Path]] = []
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CODEX_SHELL", "1")
    monkeypatch.delenv("AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT", raising=False)
    monkeypatch.setattr(
        verify_quiet.core_config,
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

    def register_wait(run_id: str, log_dir: Path) -> object:
        seen_waits.append((run_id, log_dir))
        return object()

    monkeypatch.setattr(
        verify_quiet.background_wait,
        "register_background_verifier_wait",
        register_wait,
    )
    monkeypatch.setattr(
        verify_quiet.background_wait,
        "render_background_registration_text",
        constant_callback("background verifier handoff"),
    )
    monkeypatch.setattr(
        verify_quiet,
        "make_checks",
        forbidden_callback("foreground checks should not run"),
    )

    status = verify_quiet.main(["--profile", "fast"])

    assert status == 0
    assert capsys.readouterr().out == "background verifier handoff\n"
    assert len(seen_waits) == 1
    assert seen_waits[0][0] == "async-run"


def test_codex_run_id_child_does_not_background_again(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Async verifier child runs foreground even with Codex env inherited."""

    monkeypatch.chdir(tmp_path)
    (tmp_path / "scripts").mkdir()
    monkeypatch.setenv("CODEX_SHELL", "1")
    monkeypatch.setattr(
        verify_quiet.core_config,
        "load_config",
        lambda: replace(
            MaintainerConfig(),
            source_roots=("scripts",),
            package_paths=("scripts",),
            require_tests=False,
        ),
    )
    monkeypatch.setattr(
        verify_quiet.background_wait,
        "register_background_verifier_wait",
        forbidden_callback("async child should not register background wait"),
    )
    monkeypatch.setattr(
        verify_quiet,
        "make_checks",
        constant_callback([Check("custom", ["true"], frozenset(("fast",)))]),
    )

    def successful_check(
        check: Check,
        _log_dir: Path,
        _max_lines: int,
        _max_chars: int,
    ) -> CheckResult:
        return CheckResult(check.name, passed=True, exit_code=0)

    monkeypatch.setattr(
        verify_run_steps,
        "run_check",
        successful_check,
    )

    status = verify_quiet.main(["--profile", "fast", "--run-id", "child-run"])

    assert status == 0
    assert "PASS" in capsys.readouterr().out


def fake_async_launch(_request: AsyncVerifierRequest) -> AsyncVerifierLaunch:
    """Return deterministic async verifier for CLI tests."""

    return AsyncVerifierLaunch(
        run_id="async-run",
        profile="fast",
        state_path=Path(".verify-logs/jobs/async-run.json"),
        process_id=1234,
        command=("python", "-m", "agent_maintainer", "verify"),
    )
