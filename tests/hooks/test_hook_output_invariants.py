"""Hook output invariants."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TextIO, cast

import pytest

from agent_maintainer.hooks import context as hook_context
from agent_maintainer.hooks import runtime, subprocess_runner
from tests.support.callbacks import constant_callback


def installed_repo(tmp_path: Path) -> Path:
    """Create minimal configured repository with local package entrypoint."""

    (tmp_path / "pyproject.toml").write_text("[tool.agent_maintainer]\n", encoding="utf-8")
    package_root = tmp_path / "src" / "agent_maintainer"
    package_root.mkdir(parents=True)
    (package_root / "__main__.py").write_text("", encoding="utf-8")
    return tmp_path


def write_fake_output(kwargs: dict[str, object], name: str, text: str) -> None:
    """Write fake subprocess output into a provided stream."""

    stream = kwargs.get(name)
    if hasattr(stream, "write"):
        cast(TextIO, stream).write(text)


def test_hook_verifier_output_is_streamed_and_bounded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Hook verifier output is not captured unbounded in memory."""

    installed_repo(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        "[tool.agent_maintainer]\ncontext_hook_budget_chars = 20000\n",
        encoding="utf-8",
    )
    large_output = "x" * (subprocess_runner.HOOK_SUBPROCESS_OUTPUT_LIMIT + 100)

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert kwargs.get("capture_output") is None
        write_fake_output(kwargs, "stdout", large_output)
        return subprocess.CompletedProcess(command, 1, "", "")

    def fail_pack(*_args: object, **_kwargs: object) -> hook_context.context_packs.ContextPack:
        raise OSError("pack failed")

    monkeypatch.setattr(subprocess_runner.subprocess, "run", fake_run)
    monkeypatch.setattr(runtime.hook_readiness, "hook_readiness", constant_callback(None))
    monkeypatch.setattr(hook_context.context_packs, "write_context_pack", fail_pack)

    assert (
        runtime.run_hook(
            platform=runtime.CODEX_PLATFORM,
            event=runtime.POST_TOOL_USE_EVENT,
            profile="fast",
            repo_root=tmp_path,
        )
        == 0
    )

    context = json.loads(capsys.readouterr().out)["hookSpecificOutput"]["additionalContext"]
    assert subprocess_runner.HOOK_OUTPUT_OMISSION in context
    assert len(context) < subprocess_runner.HOOK_SUBPROCESS_OUTPUT_LIMIT + 500
