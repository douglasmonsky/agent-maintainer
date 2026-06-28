"""Tests for maintainer setup diagnostics."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from agent_maintainer.core import guidance as maintainer_guidance
from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.doctor import cli as maintainer_doctor
from agent_maintainer.doctor.support import policy as maintainer_doctor_policy


def write_repo_root(tmp_path: Path) -> Path:
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "maintainer.py").write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[tool.agent_maintainer]\n", encoding="utf-8")
    return tmp_path


def test_pyright_config_check_reports_mode_mismatch(tmp_path: Path) -> None:
    (tmp_path / "pyrightconfig.json").write_text(
        '{"typeCheckingMode": "basic"}\n',
        encoding="utf-8",
    )
    config = MaintainerConfig(pyright_type_checking_mode="strict")

    result = maintainer_doctor_policy.check_pyright_config(tmp_path, config)

    assert result.status == maintainer_doctor.WARNING
    assert "basic" in result.message
    assert "strict" in result.message


def test_canonical_commands_fail_on_legacy_workflow_entrypoint(tmp_path: Path) -> None:
    workflow = tmp_path / ".github" / "workflows" / "verify.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("python3 scripts/maintainer.py verify --profile ci\n", encoding="utf-8")

    result = maintainer_doctor.check_canonical_commands(tmp_path)

    assert result.status == maintainer_doctor.ERROR
    assert ".github/workflows/verify.yml" in result.message


def test_canonical_commands_warn_for_missing_files(tmp_path: Path) -> None:
    result = maintainer_doctor.check_canonical_commands(tmp_path)

    assert result.status == maintainer_doctor.WARNING
    assert "Missing command files" in result.message


def test_canonical_commands_pass_when_all_files_use_module_entrypoint(tmp_path: Path) -> None:
    files = {
        ".github/workflows/verify.yml": "python3 -m agent_maintainer verify\n",
        ".pre-commit-config.yaml": "python3 -m agent_maintainer verify --profile precommit\n",
        ".codex/hooks/post_edit_fast_gate.py": "agent_maintainer\n",
        ".codex/hooks/stop_full_verify.py": "agent_maintainer\n",
        ".claude/settings.json": "agent_maintainer\n",
        ".claude/hooks/post_tool_use.py": "agent_maintainer\n",
        ".claude/hooks/stop.py": "agent_maintainer\n",
        ".claude/hooks/subagent_stop.py": "agent_maintainer\n",
    }
    for relative, text in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    result = maintainer_doctor.check_canonical_commands(tmp_path)

    assert result.status == maintainer_doctor.OK


def test_canonical_commands_pass_folded_yaml_entry(tmp_path: Path) -> None:
    files = {
        ".github/workflows/verify.yml": "python3 -m agent_maintainer verify\n",
        ".pre-commit-config.yaml": (
            "entry: >-\n"
            "  python3 -m agent_maintainer verify\n"
            "  --profile precommit --base-ref HEAD\n"
        ),
        ".codex/hooks/post_edit_fast_gate.py": "agent_maintainer\n",
        ".codex/hooks/stop_full_verify.py": "agent_maintainer\n",
        ".claude/settings.json": "agent_maintainer\n",
        ".claude/hooks/post_tool_use.py": "agent_maintainer\n",
        ".claude/hooks/stop.py": "agent_maintainer\n",
        ".claude/hooks/subagent_stop.py": "agent_maintainer\n",
    }
    for relative, text in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    result = maintainer_doctor.check_canonical_commands(tmp_path)

    assert result.status == maintainer_doctor.OK


def test_git_state_warns_for_dirty_ahead_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    completed = subprocess.CompletedProcess(
        ["git"],
        0,
        stdout="## main...origin/main [ahead 1]\n M README.md\n",
        stderr="",
    )
    monkeypatch.setattr(maintainer_doctor.subprocess, "run", lambda *args, **_kwargs: completed)

    result = maintainer_doctor.check_git_state(tmp_path)

    assert result.status == maintainer_doctor.WARNING
    assert "ahead 1" in result.message
    assert "changed path" in result.message


def test_git_state_warns_when_git_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(maintainer_doctor.shutil, "which", lambda name: None)

    result = maintainer_doctor.check_git_state(tmp_path)

    assert result.status == maintainer_doctor.WARNING
    assert "git executable" in result.message


def test_git_state_passes_for_clean_branch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    completed = subprocess.CompletedProcess(["git"], 0, stdout="## main...origin/main\n", stderr="")
    monkeypatch.setattr(maintainer_doctor.shutil, "which", lambda name: "/usr/bin/git")
    monkeypatch.setattr(maintainer_doctor.subprocess, "run", lambda *args, **_kwargs: completed)

    result = maintainer_doctor.check_git_state(tmp_path)

    assert result.status == maintainer_doctor.OK
    assert result.message == "main...origin/main"


def test_agent_guidance_check_warns_for_missing_custom_sidecar(tmp_path: Path) -> None:
    result = maintainer_doctor.check_agent_guidance(tmp_path, MaintainerConfig())

    assert result.status == maintainer_doctor.WARNING
    assert "AGENTS.agent-maintainer.md" in result.message


def test_agent_guidance_check_fails_for_stale_fresh_strict_sidecar(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.agent-maintainer.md").write_text("stale\n", encoding="utf-8")
    config = MaintainerConfig(mode="fresh-strict")

    result = maintainer_doctor.check_agent_guidance(tmp_path, config)

    assert result.status == maintainer_doctor.ERROR
    assert "stale" in result.message


def test_agent_guidance_check_passes_for_current_sidecar(tmp_path: Path) -> None:
    config = MaintainerConfig(mode="fresh-strict")
    expected = maintainer_guidance.render_guidance(config)
    (tmp_path / "AGENTS.agent-maintainer.md").write_text(expected, encoding="utf-8")

    result = maintainer_doctor.check_agent_guidance(tmp_path, config)

    assert result.status == maintainer_doctor.OK
