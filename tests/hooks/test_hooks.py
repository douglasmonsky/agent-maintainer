"""Tests for repo-local agent hook wrappers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

from agent_maintainer.hooks import context as hook_context
from agent_maintainer.hooks import runtime
from tests.support.paths import REPO_ROOT

HOOK_EXIT = 17


def load_hook(name: str, relative_path: str) -> ModuleType:
    """Load a repo-local hook wrapper as a module."""

    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load hook module: {relative_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("relative_path", "platform", "event", "profile"),
    (
        (".codex/hooks/post_edit_fast_gate.py", "codex", "PostToolUse", "fast"),
        (".codex/hooks/stop_full_verify.py", "codex", "Stop", "precommit"),
        (".claude/hooks/post_tool_use.py", "claude-code", "PostToolUse", "fast"),
        (".claude/hooks/stop.py", "claude-code", "Stop", "precommit"),
        (".claude/hooks/subagent_stop.py", "claude-code", "SubagentStop", "precommit"),
    ),
)
def test_hook_wrappers_delegate_to_shared_runtime(
    relative_path: str,
    platform: str,
    event: str,
    profile: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hook wrappers carry only client/event/profile metadata."""

    module = load_hook(f"hook_wrapper_{platform}_{event}", relative_path)
    calls: list[dict[str, object]] = []

    def fake_run_hook(**kwargs: object) -> int:
        calls.append(kwargs)
        return HOOK_EXIT

    monkeypatch.setattr(module, "run_hook", fake_run_hook)

    assert module.main() == HOOK_EXIT
    assert calls == [
        {
            "platform": platform,
            "event": event,
            "profile": profile,
            "repo_root": REPO_ROOT,
        }
    ]


def test_runtime_verifier_python_falls_back_to_current_interpreter(tmp_path: Path) -> None:
    """Verifier Python falls back when no virtualenv exists."""

    assert runtime.verifier_python(tmp_path) == sys.executable


def test_runtime_truncates_long_failure_output() -> None:
    """Hook output is bounded for agent feedback."""

    assert hook_context.truncate_output("abcdef", 3) == (
        "abc\n... hook output omitted 3 chars and 0 lines. Full logs are in .verify-logs/."
    )
