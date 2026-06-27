"""Tests package-first repository initializer."""

from __future__ import annotations

from pathlib import Path

from ai_guardrails.core import init_template_config, initializer
from tests.support.paths import REPO_ROOT


def test_core_init_writes_minimum_adoption_files(tmp_path: Path) -> None:
    status = initializer.main(["--target", str(tmp_path)])

    assert status == 0
    assert (tmp_path / "config" / "pyproject.guardrails.toml").exists()
    assert (tmp_path / ".pre-commit-config.yaml").exists()
    assert (tmp_path / ".github" / "workflows" / "verify.yml").exists()
    assert not (tmp_path / ".codex" / "config.toml").exists()
    config = (tmp_path / "config" / "pyproject.guardrails.toml").read_text(encoding="utf-8")
    assert 'file_length_paths = ["src", "tests", ".codex/hooks"]' in config
    assert "scripts" not in config


def test_starter_config_template_matches_initializer() -> None:
    template = (REPO_ROOT / "config" / "pyproject.guardrails.toml").read_text(encoding="utf-8")

    assert template == init_template_config.STARTER_PYPROJECT


def test_agent_init_includes_codex_hooks_and_agent_guidance(tmp_path: Path) -> None:
    status = initializer.main(["--target", str(tmp_path), "--track", "agent"])

    assert status == 0
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".codex" / "config.toml").exists()
    assert (tmp_path / ".codex" / "hooks" / "post_edit_fast_gate.py").exists()
    assert (tmp_path / ".codex" / "hooks" / "stop_full_verify.py").exists()
    assert "python3 -m ai_guardrails" in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    stop_hook = (tmp_path / ".codex" / "hooks" / "stop_full_verify.py").read_text(
        encoding="utf-8",
    )
    assert "Final verification failed. Fix issues before finishing." in stop_hook
    assert "separator = chr(10) * 2" in stop_hook
    assert "{separator}{output[:8000]}" in stop_hook


def test_hardening_init_adds_node_backed_tooling_files(tmp_path: Path) -> None:
    status = initializer.main(["--target", str(tmp_path), "--track", "hardening"])

    assert status == 0
    assert (tmp_path / "package.json").exists()
    assert "markdownlint-cli2" in (tmp_path / "package.json").read_text(encoding="utf-8")


def test_init_refuses_existing_files_without_force(tmp_path: Path) -> None:
    existing = tmp_path / ".pre-commit-config.yaml"
    existing.write_text("existing\n", encoding="utf-8")

    status = initializer.main(["--target", str(tmp_path)])

    assert status == 1
    assert existing.read_text(encoding="utf-8") == "existing\n"


def test_dry_run_does_not_write_files(tmp_path: Path) -> None:
    status = initializer.main(["--target", str(tmp_path), "--dry-run"])

    assert status == 0
    assert not (tmp_path / "config").exists()
