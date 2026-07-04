"""Tests hook runtime same-state verifier readiness reuse."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from agent_maintainer.hooks import runtime


def installed_repo(tmp_path: Path) -> Path:
    """Create minimal configured repository with local package entrypoint."""
    (tmp_path / "pyproject.toml").write_text("[tool.agent_maintainer]\n", encoding="utf-8")
    package_root = tmp_path / "src" / "agent_maintainer"
    package_root.mkdir(parents=True)
    (package_root / "__main__.py").write_text("", encoding="utf-8")
    return tmp_path


def test_runtime_reports_pending_same_state_verifier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Hooks point to in-flight same-state verifier instead of rerunning."""
    installed_repo(tmp_path)

    def fail_verifier(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        pytest.fail("same-state pending verifier should not run again")
        return subprocess.CompletedProcess([], 99, "", "")

    monkeypatch.setattr(runtime.hook_subprocess, "run_verifier_bounded", fail_verifier)
    monkeypatch.setattr(
        runtime.hook_readiness,
        "hook_readiness",
        lambda _repo_root, profile: runtime.hook_readiness.HookReadiness(
            status="pending",
            profile=profile,
            run_id="run-pending",
        ),
    )

    status = runtime.run_hook(
        platform=runtime.CODEX_PLATFORM,
        event=runtime.POST_TOOL_USE_EVENT,
        profile="fast",
        repo_root=tmp_path,
    )

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["decision"] == "block"
    assert "already running" in payload["reason"]
    assert "wait verifier run-pending" in payload["hookSpecificOutput"]["additionalContext"]


def test_runtime_reuses_completed_same_state_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Stop hook continues when same-state verifier already passed."""
    installed_repo(tmp_path)

    def fail_verifier(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        pytest.fail("same-state completed verifier should not run again")
        return subprocess.CompletedProcess([], 99, "", "")

    monkeypatch.setattr(runtime.hook_subprocess, "run_verifier_bounded", fail_verifier)
    monkeypatch.setattr(
        runtime.hook_readiness,
        "hook_readiness",
        lambda _repo_root, profile: runtime.hook_readiness.HookReadiness(
            status="completed",
            profile=profile,
            run_id="run-pass",
            exit_code=0,
        ),
    )

    status = runtime.run_hook(
        platform=runtime.CLAUDE_CODE_PLATFORM,
        event=runtime.STOP_EVENT,
        profile="precommit",
        repo_root=tmp_path,
    )

    assert status == 0
    assert json.loads(capsys.readouterr().out) == {"continue": True}


def test_runtime_reuses_completed_same_state_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Stop hook blocks with completed same-state verifier failure."""
    installed_repo(tmp_path)

    def fail_verifier(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        pytest.fail("same-state failed verifier should not run again")
        return subprocess.CompletedProcess([], 99, "", "")

    monkeypatch.setattr(runtime.hook_subprocess, "run_verifier_bounded", fail_verifier)
    monkeypatch.setattr(
        runtime.hook_readiness,
        "hook_readiness",
        lambda _repo_root, profile: runtime.hook_readiness.HookReadiness(
            status="completed",
            profile=profile,
            run_id="run-fail",
            exit_code=1,
        ),
    )

    status = runtime.run_hook(
        platform=runtime.CLAUDE_CODE_PLATFORM,
        event=runtime.STOP_EVENT,
        profile="precommit",
        repo_root=tmp_path,
    )

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["decision"] == "block"
    assert "wait verifier run-fail" in payload["reason"]
