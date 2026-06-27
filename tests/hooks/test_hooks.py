"""Tests for Codex hook wrappers."""

from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from tests.support.paths import REPO_ROOT


def load_hook(name: str, relative_path: str) -> ModuleType:
    path = REPO_ROOT / relative_path
    hook_dir = str(path.parent)
    if hook_dir not in sys.path:
        sys.path.insert(0, hook_dir)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load hook module: {relative_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def capture_audit(module: ModuleType, monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    records: list[Any] = []

    def fake_record_hook_result(_repo_root: Path, record: Any) -> None:
        records.append(record)

    monkeypatch.setattr(module, "record_hook_result", fake_record_hook_result)
    return records


class FakeHookPath:
    """Minimal Path stand-in for hook repo-root tests."""

    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root

    def resolve(self) -> FakeHookPath:
        return self

    @property
    def parents(self) -> list[Path | None]:
        return [None, None, self._repo_root]


def test_post_hook_verifier_python_falls_back_to_current_interpreter(
    tmp_path: Path,
) -> None:
    post_hook = load_hook(
        "post_edit_fast_gate_python_fallback_test",
        ".codex/hooks/post_edit_fast_gate.py",
    )

    assert post_hook.verifier_python(tmp_path) == sys.executable


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
    records = capture_audit(post_hook, monkeypatch)

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert command[-2:] == ["--base-ref", "HEAD"]
        env = _kwargs["env"]
        assert isinstance(env, dict)
        assert env["PYTHONDONTWRITEBYTECODE"] == "1"
        return subprocess.CompletedProcess(command, 1, "failed", "")

    monkeypatch.setattr(post_hook.subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "stdin", io.StringIO("{not json"))

    assert post_hook.main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["decision"] == "block"
    assert "failed" in payload["hookSpecificOutput"]["additionalContext"]
    assert records[0].hook_name == "PostToolUse"
    assert records[0].profile == "fast"
    assert records[0].status == "failed"


def test_post_hook_truncates_long_failure_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    post_hook = load_hook(
        "post_edit_fast_gate_truncation_test",
        ".codex/hooks/post_edit_fast_gate.py",
    )
    records = capture_audit(post_hook, monkeypatch)

    def fake_run(
        command: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 1, "x" * 24, "")

    monkeypatch.setattr(post_hook, "MAX_CONTEXT", 5)
    monkeypatch.setattr(post_hook.subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "stdin", io.StringIO("not-json"))

    assert post_hook.main() == 0

    payload = json.loads(capsys.readouterr().out)
    context = payload["hookSpecificOutput"]["additionalContext"]
    assert "xxxxx" in context
    assert "truncated" in context
    assert records[0].status == "failed"


def test_post_hook_audits_missing_verifier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    post_hook = load_hook(
        "post_edit_fast_gate_missing_verifier_test",
        ".codex/hooks/post_edit_fast_gate.py",
    )
    records = capture_audit(post_hook, monkeypatch)

    monkeypatch.setattr(post_hook, "Path", lambda _value: FakeHookPath(tmp_path))
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))

    assert post_hook.main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["decision"] == "block"
    assert records[0].hook_name == "PostToolUse"
    assert records[0].reason == "missing verifier"


def test_post_hook_main_allows_success(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    post_hook = load_hook("post_edit_fast_gate_success_test", ".codex/hooks/post_edit_fast_gate.py")
    records = capture_audit(post_hook, monkeypatch)

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert command[-2:] == ["--base-ref", "HEAD"]
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(post_hook.subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))

    assert post_hook.main() == 0
    assert capsys.readouterr().out == ""
    assert records[0].hook_name == "PostToolUse"
    assert records[0].profile == "fast"
    assert records[0].status == "passed"


def test_stop_hook_verifier_python_falls_back_to_current_interpreter(
    tmp_path: Path,
) -> None:
    stop_hook = load_hook(
        "stop_full_verify_python_fallback_test",
        ".codex/hooks/stop_full_verify.py",
    )

    assert stop_hook.verifier_python(tmp_path) == sys.executable


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
    records = capture_audit(stop_hook, monkeypatch)

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert command[-2:] == ["--base-ref", "HEAD"]
        env = _kwargs["env"]
        assert isinstance(env, dict)
        assert env["PYTHONDONTWRITEBYTECODE"] == "1"
        return subprocess.CompletedProcess(command, 1, "precommit failed", "")

    monkeypatch.setattr(stop_hook.subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))

    assert stop_hook.main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["decision"] == "block"
    assert "precommit failed" in payload["reason"]
    assert records[0].hook_name == "Stop"
    assert records[0].profile == "precommit"
    assert records[0].status == "failed"


def test_stop_hook_treats_malformed_stdin_as_empty_payload(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    stop_hook = load_hook(
        "stop_full_verify_bad_stdin_test",
        ".codex/hooks/stop_full_verify.py",
    )
    records = capture_audit(stop_hook, monkeypatch)

    def fake_run(
        command: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(stop_hook.subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "stdin", io.StringIO("{"))

    assert stop_hook.main() == 0
    assert json.loads(capsys.readouterr().out) == {"continue": True}
    assert records[0].status == "passed"


def test_stop_hook_truncates_long_failure_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    stop_hook = load_hook(
        "stop_full_verify_truncation_test",
        ".codex/hooks/stop_full_verify.py",
    )
    records = capture_audit(stop_hook, monkeypatch)

    def fake_run(
        command: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 1, "x" * 24, "")

    monkeypatch.setattr(stop_hook, "MAX_CONTEXT", 5)
    monkeypatch.setattr(stop_hook.subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))

    assert stop_hook.main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert "xxxxx" in payload["reason"]
    assert "truncated" in payload["reason"]
    assert records[0].status == "failed"


def test_stop_hook_audits_missing_verifier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    stop_hook = load_hook(
        "stop_full_verify_missing_verifier_test",
        ".codex/hooks/stop_full_verify.py",
    )
    records = capture_audit(stop_hook, monkeypatch)

    monkeypatch.setattr(stop_hook, "Path", lambda _value: FakeHookPath(tmp_path))
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))

    assert stop_hook.main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["decision"] == "block"
    assert records[0].hook_name == "Stop"
    assert records[0].reason == "missing verifier"


def test_stop_hook_allows_success(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    stop_hook = load_hook("stop_full_verify_success_test", ".codex/hooks/stop_full_verify.py")
    records = capture_audit(stop_hook, monkeypatch)

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert command[-2:] == ["--base-ref", "HEAD"]
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(stop_hook.subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))

    assert stop_hook.main() == 0
    assert json.loads(capsys.readouterr().out) == {"continue": True}
    assert records[0].hook_name == "Stop"
    assert records[0].profile == "precommit"
    assert records[0].status == "passed"
