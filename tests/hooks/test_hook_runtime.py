"""Tests for shared agent hook runtime."""

from __future__ import annotations

import json
import subprocess
import sys
from io import StringIO
from pathlib import Path

import pytest

from agent_maintainer.hooks import audit, runtime
from agent_maintainer.hooks import context as hook_context

HOOK_STATUS = 23


def configured_repo(tmp_path: Path) -> Path:
    """Create a minimal maintainer-configured repository."""

    (tmp_path / "pyproject.toml").write_text("[tool.agent_maintainer]\n", encoding="utf-8")
    return tmp_path


def installed_repo(tmp_path: Path) -> Path:
    """Create a minimal configured repository with local package entrypoint."""

    configured_repo(tmp_path)
    package_root = tmp_path / "src" / "agent_maintainer"
    package_root.mkdir(parents=True)
    (package_root / "__main__.py").write_text("", encoding="utf-8")
    return tmp_path


def write_failure_manifest(repo_root: Path, check_name: str) -> None:
    """Write verifier failure manifest consumed by context packs."""

    log_dir = repo_root / ".verify-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / f"{check_name}.log").write_text("failure log\n", encoding="utf-8")
    manifest = {
        "checks": [
            {
                "name": check_name,
                "status": "failed",
                "exit_code": 1,
                "log_path": str(log_dir / f"{check_name}.log"),
            },
        ],
    }
    (log_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_runtime_noops_without_repo_opt_in(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Global/user hooks skip repositories without maintainer config."""

    def fail_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        pytest.fail("unconfigured repository should not run verification")

    monkeypatch.setattr(runtime.subprocess, "run", fail_run)

    status = runtime.run_hook(
        platform=runtime.CLAUDE_CODE_PLATFORM,
        event=runtime.STOP_EVENT,
        profile="precommit",
        repo_root=tmp_path,
    )

    assert status == 0
    assert not (tmp_path / ".verify-logs").exists()


def test_discover_repo_root_falls_back_without_git(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repo discovery falls back when git executable is unavailable."""

    monkeypatch.setattr(runtime.shutil, "which", lambda _name: None)

    assert runtime.discover_repo_root(tmp_path) == tmp_path


def test_discover_repo_root_uses_git_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repo discovery uses absolute git executable output when available."""

    expected = tmp_path / "repo"

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert command == ["/usr/bin/git", "rev-parse", "--show-toplevel"]
        assert kwargs["cwd"] == tmp_path
        return subprocess.CompletedProcess(command, 0, f"{expected}\n", "")

    monkeypatch.setattr(runtime.shutil, "which", lambda _name: "/usr/bin/git")
    monkeypatch.setattr(runtime.subprocess, "run", fake_run)

    assert runtime.discover_repo_root(tmp_path) == expected


def test_main_dispatches_to_run_hook(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Runtime CLI parses arguments and delegates to run_hook."""

    calls: list[dict[str, object]] = []

    def fake_run_hook(**kwargs: object) -> int:
        calls.append(kwargs)
        return HOOK_STATUS

    monkeypatch.setattr(runtime, "run_hook", fake_run_hook)

    status = runtime.main(
        [
            "--platform",
            runtime.CODEX_PLATFORM,
            "--event",
            runtime.POST_TOOL_USE_EVENT,
            "--profile",
            "fast",
            "--repo-root",
            str(tmp_path),
        ]
    )

    assert status == HOOK_STATUS
    assert calls == [
        {
            "platform": runtime.CODEX_PLATFORM,
            "event": runtime.POST_TOOL_USE_EVENT,
            "profile": "fast",
            "repo_root": tmp_path,
        }
    ]


def test_recursive_stop_payload_continues(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Recursive stop events continue without running verification."""

    monkeypatch.setattr(sys, "stdin", StringIO('{"stop_hook_active": true}'))

    assert (
        runtime.run_hook(
            platform=runtime.CODEX_PLATFORM,
            event=runtime.STOP_EVENT,
            profile="precommit",
            repo_root=tmp_path,
        )
        == 0
    )

    assert json.loads(capsys.readouterr().out) == {"continue": True}


def test_malformed_payload_does_not_block_unconfigured_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed hook JSON is treated as an empty payload."""

    monkeypatch.setattr(sys, "stdin", StringIO("{"))

    assert (
        runtime.run_hook(
            platform=runtime.CODEX_PLATFORM,
            event=runtime.STOP_EVENT,
            profile="precommit",
            repo_root=tmp_path,
        )
        == 0
    )


def test_missing_verifier_blocks_and_records_reason(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Configured repos block when neither local package nor console command exists."""

    configured_repo(tmp_path)
    monkeypatch.setattr(runtime, "package_command_available", lambda: False)

    assert (
        runtime.run_hook(
            platform=runtime.CLAUDE_CODE_PLATFORM,
            event=runtime.STOP_EVENT,
            profile="precommit",
            repo_root=tmp_path,
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["decision"] == "block"
    assert "verifier missing" in payload["reason"]
    audit_payload = json.loads((tmp_path / ".verify-logs" / "hooks.jsonl").read_text())
    assert audit_payload["reason"] == "missing verifier"
    assert audit_payload["platform"] == runtime.CLAUDE_CODE_PLATFORM


def test_failed_post_tool_use_blocks_with_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """PostToolUse failures emit hook-specific context pack pointer."""

    installed_repo(tmp_path)
    write_failure_manifest(tmp_path, "pyright")

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 1, "post failed", "")

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)

    assert (
        runtime.run_hook(
            platform=runtime.CODEX_PLATFORM,
            event=runtime.POST_TOOL_USE_EVENT,
            profile="fast",
            repo_root=tmp_path,
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    context = payload["hookSpecificOutput"]["additionalContext"]
    assert payload["decision"] == "block"
    assert payload["hookSpecificOutput"]["hookEventName"] == runtime.POST_TOOL_USE_EVENT
    assert "Read: .verify-logs/context/PACK.md" in context
    assert "Top finding: pyright:" in context
    assert "Expand: python -m agent_maintainer context failures" in context
    assert "post failed" not in context
    assert (tmp_path / ".verify-logs" / "context" / "PACK.md").exists()


@pytest.mark.parametrize("event", (runtime.STOP_EVENT, runtime.SUBAGENT_STOP_EVENT))
def test_failed_stop_events_block_with_context_pack(
    event: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Stop-like failures put context pack pointer in block reason."""

    installed_repo(tmp_path)
    write_failure_manifest(tmp_path, "ruff")

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 1, "", "stop failed")

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)

    assert (
        runtime.run_hook(
            platform=runtime.CODEX_PLATFORM,
            event=event,
            profile="precommit",
            repo_root=tmp_path,
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["decision"] == "block"
    assert "Final verification failed" in payload["reason"]
    assert "Read: .verify-logs/context/PACK.md" in payload["reason"]
    assert "Top finding: ruff:" in payload["reason"]
    assert "stop failed" not in payload["reason"]


def test_hook_failure_falls_back_when_context_pack_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Hook failure falls back to bounded verifier output when pack fails."""

    installed_repo(tmp_path)

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 1, "raw failure", "")

    def fail_pack(*_args: object, **_kwargs: object) -> hook_context.context_packs.ContextPack:
        raise OSError("pack failed")

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)
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
    assert "raw failure" in context
    assert "Context pack generation failed: pack failed" in context


def test_hook_context_pack_pointer_respects_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Hook context pack pointer remains bounded by hook budget."""

    installed_repo(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        "[tool.agent_maintainer]\ncontext_hook_budget_chars = 40\n",
        encoding="utf-8",
    )
    pack = hook_context.context_packs.ContextPack(
        markdown="",
        payload={},
        markdown_path=tmp_path / ".verify-logs" / "context" / "PACK.md",
        json_path=tmp_path / ".verify-logs" / "context" / "PACK.json",
    )

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 1, "failed", "")

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)
    monkeypatch.setattr(hook_context.context_packs, "write_context_pack", lambda *_args: pack)
    monkeypatch.setattr(
        hook_context.pack_rendering, "render_pack_pointer", lambda *_args, **_kwargs: "x" * 200
    )

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
    assert "hook output omitted" in context


def test_hook_context_display_path_falls_back_to_absolute(tmp_path: Path) -> None:
    """Hook context display path handles paths outside repo root."""

    outside_path = tmp_path.parent / "outside-pack.md"

    assert hook_context.display_path(outside_path, tmp_path) == str(outside_path)


def test_verifier_helpers_cover_virtualenv_and_global_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifier helper branches find virtualenv and fallback package command."""

    python_path = tmp_path / ".venv" / "bin" / "python"
    python_path.parent.mkdir(parents=True)
    python_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(runtime.shutil, "which", lambda name: f"/bin/{name}")

    assert runtime.verifier_python(tmp_path) == str(python_path)
    assert runtime.package_command_available()
    assert runtime.verifier_available(tmp_path)


def test_audit_helpers_include_reason_and_custom_log_dir(tmp_path: Path) -> None:
    """Audit payloads include reasons and respect configured diagnostic dir."""

    record = audit.HookAuditRecord(
        hook_name="Stop",
        profile="precommit",
        status="failed",
        command=("agent-maintainer", "verify"),
        exit_code=1,
        started_at="2026-01-01T00:00:00Z",
        ended_at="2026-01-01T00:00:01Z",
        duration_seconds=1.0,
        reason="failed",
    )
    (tmp_path / "pyproject.toml").write_text(
        "[tool.agent_maintainer.diagnostics]\nlog_dir = '.logs'\n",
        encoding="utf-8",
    )

    assert record.to_payload()["reason"] == "failed"
    assert audit.configured_log_dir(tmp_path) == ".logs"


def test_runtime_records_platform_in_hook_audit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Shared hook runtime records client platform."""

    (tmp_path / "src" / "agent_maintainer").mkdir(parents=True)
    (tmp_path / "src" / "agent_maintainer" / "__main__.py").write_text(
        "",
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text("[tool.agent_maintainer]\n", encoding="utf-8")

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)

    status = runtime.run_hook(
        platform=runtime.CLAUDE_CODE_PLATFORM,
        event=runtime.POST_TOOL_USE_EVENT,
        profile="fast",
        repo_root=tmp_path,
    )

    assert status == 0
    payload = json.loads((tmp_path / ".verify-logs" / "hooks.jsonl").read_text())
    assert payload["platform"] == "claude-code"
    assert payload["hook"] == "PostToolUse"
