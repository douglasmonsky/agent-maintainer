"""Tests for Codex hook audit JSONL helpers."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

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


def test_record_hook_result_uses_configured_diagnostics_dir(tmp_path: Path) -> None:
    hook_audit = load_hook("hook_audit_writer_test", ".codex/hooks/hook_audit.py")
    (tmp_path / "pyproject.toml").write_text(
        '[tool.ai_guardrails.diagnostics]\nlog_dir = ".custom-logs"\n',
        encoding="utf-8",
    )
    record = hook_audit.HookAuditRecord(
        hook_name="PostToolUse",
        profile="fast",
        status="passed",
        command=("python3", "-m", "ai_guardrails"),
        exit_code=0,
        started_at="2026-06-25T10:00:00Z",
        ended_at="2026-06-25T10:00:01Z",
        duration_seconds=1.0,
    )

    hook_audit.record_hook_result(tmp_path, record)

    audit_path = tmp_path / ".custom-logs" / "hooks.jsonl"
    payload = json.loads(audit_path.read_text(encoding="utf-8"))
    assert payload["hook"] == "PostToolUse"
    assert payload["status"] == "passed"
    assert payload["command"] == ["python3", "-m", "ai_guardrails"]


def test_status_for_exit_marks_nonzero_and_missing_as_failed() -> None:
    hook_audit = load_hook("hook_audit_status_test", ".codex/hooks/hook_audit.py")

    assert hook_audit.status_for_exit(0) == "passed"
    assert hook_audit.status_for_exit(1) == "failed"
    assert hook_audit.status_for_exit(None) == "failed"
