"""Tests hook context budget handling."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from agent_maintainer.hooks import runtime, subprocess_runner

HOOK_CONTEXT_LIMIT = 120


def configured_installed_repo(tmp_path: Path) -> Path:
    """Create repo configured for hook runtime with local package marker."""

    (tmp_path / "pyproject.toml").write_text(
        f"[tool.agent_maintainer]\ncontext_hook_budget_chars = {HOOK_CONTEXT_LIMIT}\n",
        encoding="utf-8",
    )
    package_root = tmp_path / "src" / "agent_maintainer"
    package_root.mkdir(parents=True)
    (package_root / "__main__.py").write_text("", encoding="utf-8")
    return tmp_path


def test_hook_failure_output_uses_context_hook_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Hook block context is capped by configured context hook budget."""

    repo_root = configured_installed_repo(tmp_path)
    large_output = "x" * (HOOK_CONTEXT_LIMIT * 3)

    def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess([], 1, large_output, "")

    monkeypatch.setattr(subprocess_runner.subprocess, "run", fake_run)

    status = runtime.run_hook(
        platform=runtime.CLAUDE_CODE_PLATFORM,
        event=runtime.STOP_EVENT,
        profile="precommit",
        repo_root=repo_root,
    )

    payload = json.loads(capsys.readouterr().out)

    assert status == 0
    assert payload["decision"] == "block"
    assert len(payload["reason"]) < len(large_output)
    assert "omitted" in payload["reason"]
    assert ".verify-logs/" in payload["reason"]
