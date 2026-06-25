"""Tests for Codex hook wrappers."""

from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def load_hook(name: str, relative_path: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / relative_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load hook module: {relative_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_post_hook_emits_block_payload(capsys: pytest.CaptureFixture[str]) -> None:
    post_hook = load_hook("post_edit_fast_gate_test", ".codex/hooks/post_edit_fast_gate.py")

    assert post_hook.emit_block("reason", "context") == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["decision"] == "block"
    assert payload["hookSpecificOutput"]["hookEventName"] == "PostToolUse"


def test_post_hook_main_blocks_on_failed_verification(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    post_hook = load_hook("post_edit_fast_gate_failure_test", ".codex/hooks/post_edit_fast_gate.py")

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert command[-2:] == ["--base-ref", "HEAD"]
        return subprocess.CompletedProcess(command, 1, "failed", "")

    monkeypatch.setattr(post_hook.subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "stdin", io.StringIO("{not json"))

    assert post_hook.main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["decision"] == "block"
    assert "failed" in payload["hookSpecificOutput"]["additionalContext"]


def test_post_hook_main_allows_success(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    post_hook = load_hook("post_edit_fast_gate_success_test", ".codex/hooks/post_edit_fast_gate.py")

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert command[-2:] == ["--base-ref", "HEAD"]
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(post_hook.subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))

    assert post_hook.main() == 0
    assert capsys.readouterr().out == ""


def test_stop_hook_allows_recursive_stop_hook(capsys: pytest.CaptureFixture[str]) -> None:
    stop_hook = load_hook("stop_full_verify_recursive_test", ".codex/hooks/stop_full_verify.py")
    original_stdin = sys.stdin
    sys.stdin = io.StringIO('{"stop_hook_active": true}')
    try:
        assert stop_hook.main() == 0
    finally:
        sys.stdin = original_stdin

    assert json.loads(capsys.readouterr().out) == {"continue": True}


def test_stop_hook_blocks_on_failed_verification(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    stop_hook = load_hook("stop_full_verify_failure_test", ".codex/hooks/stop_full_verify.py")

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert command[-2:] == ["--base-ref", "HEAD"]
        return subprocess.CompletedProcess(command, 1, "precommit failed", "")

    monkeypatch.setattr(stop_hook.subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))

    assert stop_hook.main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["decision"] == "block"
    assert "precommit failed" in payload["reason"]


def test_stop_hook_allows_success(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    stop_hook = load_hook("stop_full_verify_success_test", ".codex/hooks/stop_full_verify.py")

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert command[-2:] == ["--base-ref", "HEAD"]
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(stop_hook.subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))

    assert stop_hook.main() == 0
    assert json.loads(capsys.readouterr().out) == {"continue": True}
