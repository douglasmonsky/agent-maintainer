"""Tests for package-first repository initializer."""

from __future__ import annotations

import py_compile
from pathlib import Path

from yamllint import linter
from yamllint.config import YamlLintConfig

from agent_maintainer.core import init_template_config, initializer
from tests.support.paths import REPO_ROOT

STARTER_CONFIG = Path("config") / "pyproject.agent-maintainer.toml"


def test_core_init_writes_minimum_adoption_files(tmp_path: Path) -> None:
    """Core track writes the package-first minimum starter files."""

    status = initializer.main(["--target", str(tmp_path)])

    assert status == 0
    assert (tmp_path / STARTER_CONFIG).exists()
    assert (tmp_path / "config" / "dev-dependencies.txt").exists()
    assert (tmp_path / ".pre-commit-config.yaml").exists()
    assert (tmp_path / ".github" / "workflows" / "verify.yml").exists()
    assert not (tmp_path / ".codex" / "config.toml").exists()

    config = (tmp_path / STARTER_CONFIG).read_text(encoding="utf-8")
    dependencies = (tmp_path / "config" / "dev-dependencies.txt").read_text(encoding="utf-8")
    workflow = (tmp_path / ".github" / "workflows" / "verify.yml").read_text(encoding="utf-8")
    assert "[tool.agent_maintainer]" in config
    assert 'file_length_paths = ["src", "tests", ".codex/hooks", ".claude/hooks"]' in config
    assert "agent-maintainer[core]" in dependencies
    assert 'python-version: "3.11"' in workflow
    assert 'BASE_REF="origin/${GITHUB_BASE_REF:-main}"' in workflow
    assert "verify --profile ci \\" in workflow
    assert '--base-ref "$BASE_REF"' in workflow
    assert '--compare-branch "$BASE_REF"' in workflow
    assert "python -m pip install -e ." in workflow
    assert "--no-deps" not in workflow
    assert "scripts" not in config
    yaml_config = YamlLintConfig((REPO_ROOT / ".yamllint").read_text(encoding="utf-8"))
    workflow_path = tmp_path / ".github" / "workflows" / "verify.yml"
    problems = list(linter.run(workflow, yaml_config, filepath=str(workflow_path)))
    assert not problems, "\n".join(str(problem) for problem in problems)


def test_starter_config_template_matches_initializer() -> None:
    """The committed starter template matches the initializer payload."""

    template = (REPO_ROOT / STARTER_CONFIG).read_text(encoding="utf-8")

    assert template == init_template_config.STARTER_PYPROJECT


def test_agent_init_includes_codex_hooks_and_agent_guidance(tmp_path: Path) -> None:
    """Agent track writes AGENTS guidance and syntactically valid agent hooks."""

    status = initializer.main(["--target", str(tmp_path), "--track", "agent"])

    assert status == 0
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".codex" / "config.toml").exists()
    assert (tmp_path / ".claude" / "settings.json").exists()

    post_hook = tmp_path / ".codex" / "hooks" / "post_edit_fast_gate.py"
    stop_hook = tmp_path / ".codex" / "hooks" / "stop_full_verify.py"
    claude_post_hook = tmp_path / ".claude" / "hooks" / "post_tool_use.py"
    claude_stop_hook = tmp_path / ".claude" / "hooks" / "stop.py"
    claude_subagent_hook = tmp_path / ".claude" / "hooks" / "subagent_stop.py"
    assert post_hook.exists()
    assert stop_hook.exists()
    assert claude_post_hook.exists()
    assert claude_stop_hook.exists()
    assert claude_subagent_hook.exists()
    py_compile.compile(str(post_hook), doraise=True)
    py_compile.compile(str(stop_hook), doraise=True)
    py_compile.compile(str(claude_post_hook), doraise=True)
    py_compile.compile(str(claude_stop_hook), doraise=True)
    py_compile.compile(str(claude_subagent_hook), doraise=True)

    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "AGENTS.agent-maintainer.md" in agents
    assert "python3 -m agent_maintainer" in agents
    assert "agent_maintainer" in stop_hook.read_text(encoding="utf-8")


def test_hardening_init_includes_package_metadata(tmp_path: Path) -> None:
    """Hardening track adds npm metadata without overwriting core files."""

    status = initializer.main(["--target", str(tmp_path), "--track", "hardening"])

    assert status == 0
    assert (tmp_path / STARTER_CONFIG).exists()
    assert (tmp_path / "package.json").exists()
    assert (tmp_path / ".codex" / "hooks" / "stop_full_verify.py").exists()
    assert (tmp_path / ".claude" / "hooks" / "stop.py").exists()


def test_initializer_refuses_overwrite_without_force(tmp_path: Path) -> None:
    """Existing generated files are left alone unless --force is explicit."""

    config_path = tmp_path / STARTER_CONFIG
    config_path.parent.mkdir(parents=True)
    config_path.write_text("existing", encoding="utf-8")

    status = initializer.main(["--target", str(tmp_path)])

    assert status == 1
    assert config_path.read_text(encoding="utf-8") == "existing"


def test_initializer_dry_run_writes_nothing(tmp_path: Path) -> None:
    """Dry-run reports planned writes without creating files."""

    status = initializer.main(["--target", str(tmp_path), "--dry-run"])

    assert status == 0
    assert not (tmp_path / "config").exists()
    assert not (tmp_path / ".pre-commit-config.yaml").exists()
