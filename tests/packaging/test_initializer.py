"""Tests for package-first repository initializer."""

from __future__ import annotations

import py_compile
import tomllib
from pathlib import Path

from yamllint import linter
from yamllint.config import YamlLintConfig

from agent_maintainer.core.scaffold import initializer, template_config, templates
from tests.support.paths import REPO_ROOT

STARTER_CONFIG = Path("config") / "pyproject.agent-maintainer.toml"


# docsync:evidence.start evidence.readme.initializer_tests
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
    assert "python -m pip install -e ." not in workflow
    assert "if [ -f package.json ]; then" in workflow
    assert "npm ci" in workflow
    assert "--no-deps" not in workflow
    assert "scripts" not in config
    yaml_config = YamlLintConfig((REPO_ROOT / ".yamllint").read_text(encoding="utf-8"))
    workflow_path = tmp_path / ".github" / "workflows" / "verify.yml"
    problems = list(linter.run(workflow, yaml_config, filepath=str(workflow_path)))
    assert not problems, "\n".join(str(problem) for problem in problems)


def test_starter_config_template_matches_initializer() -> None:
    """The committed starter template matches the initializer payload."""

    template = (REPO_ROOT / STARTER_CONFIG).read_text(encoding="utf-8")

    assert template == template_config.STARTER_PYPROJECT


def test_ci_only_init_writes_workflow_adoption_files(tmp_path: Path) -> None:
    """CI-only mode writes GitHub Actions files without local hook setup."""

    status = initializer.main(["--target", str(tmp_path), "--ci-only"])

    assert status == 0
    assert (tmp_path / "config" / "dev-dependencies.txt").exists()
    assert (tmp_path / ".github" / "workflows" / "verify.yml").exists()
    assert not (tmp_path / STARTER_CONFIG).exists()
    assert not (tmp_path / ".pre-commit-config.yaml").exists()
    assert not (tmp_path / ".codex" / "config.toml").exists()

    workflow = (tmp_path / ".github" / "workflows" / "verify.yml").read_text(encoding="utf-8")
    assert "python -m pip install -r config/dev-dependencies.txt" in workflow
    assert "python -m pip install -e ." not in workflow


def test_ci_only_starter_files_are_minimal() -> None:
    """CI-only starter files stay limited to workflow dependencies."""

    assert {starter.path for starter in templates.ci_starter_files()} == {
        ".github/workflows/verify.yml",
        "config/dev-dependencies.txt",
    }


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
    package_json = (tmp_path / "package.json").read_text(encoding="utf-8")
    workflow = (tmp_path / ".github" / "workflows" / "verify.yml").read_text(encoding="utf-8")

    assert '"markdownlint-cli2"' in package_json
    assert '"@taplo/cli"' in package_json
    assert "if [ -f package.json ]; then" in workflow
    assert "npm ci" in workflow
    assert (tmp_path / ".codex" / "hooks" / "stop_full_verify.py").exists()
    assert (tmp_path / ".claude" / "hooks" / "stop.py").exists()


# docsync:evidence.end evidence.readme.initializer_tests


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


PRESET_EXPECTATIONS = {
    "small-library": {
        "mode": "custom",
        "coverage_fail_under": 90,
        "change_warn_lines": 200,
        "change_block_files": 12,
        "suppression_max_new": 1,
        "ruff_max_complexity": 8,
        "ratchet_enabled": False,
        "enable_wemake": False,
    },
    "existing-app": {
        "mode": "custom",
        "coverage_fail_under": 80,
        "change_warn_lines": 300,
        "change_block_files": 20,
        "suppression_max_new": 3,
        "ruff_max_complexity": 10,
        "ratchet_enabled": False,
        "enable_wemake": False,
    },
    "ai-agent-heavy": {
        "mode": "fresh-strict",
        "coverage_fail_under": 90,
        "change_warn_lines": 200,
        "change_block_files": 12,
        "source_without_test_change_error_profiles": ["precommit", "full", "ci"],
        "suppression_max_new": 1,
        "ratchet_enabled": False,
        "enable_wemake": False,
    },
    "legacy-ratchet": {
        "mode": "legacy-ratchet",
        "coverage_fail_under": 70,
        "diff_cover_fail_under": 80,
        "change_warn_lines": 500,
        "change_block_files": 30,
        "suppression_max_new": 5,
        "ratchet_enabled": True,
        "file_length_baseline": ".agent-maintainer/file-length-baseline.json",
    },
    "strict-new-repo": {
        "mode": "fresh-strict",
        "coverage_fail_under": 90,
        "change_warn_lines": 150,
        "change_block_files": 10,
        "source_without_test_change_error_profiles": ["precommit", "full", "ci"],
        "suppression_max_new": 0,
        "pyright_type_checking_mode": "strict",
        "ratchet_enabled": False,
        "enable_wemake": True,
    },
    "team-small-python-lib": {
        "mode": "custom",
        "coverage_fail_under": 90,
        "change_warn_lines": 200,
        "change_block_files": 12,
        "suppression_max_new": 1,
        "ruff_max_complexity": 8,
        "ratchet_enabled": False,
        "enable_wemake": False,
    },
    "team-legacy-service": {
        "mode": "legacy-ratchet",
        "coverage_fail_under": 70,
        "diff_cover_fail_under": 80,
        "change_warn_lines": 500,
        "change_block_files": 30,
        "suppression_max_new": 5,
        "ratchet_enabled": True,
        "file_length_baseline": ".agent-maintainer/file-length-baseline.json",
    },
    "team-agent-heavy": {
        "mode": "fresh-strict",
        "coverage_fail_under": 90,
        "change_warn_lines": 200,
        "change_block_files": 12,
        "source_without_test_change_error_profiles": ["precommit", "full", "ci"],
        "suppression_max_new": 1,
        "ratchet_enabled": False,
        "enable_wemake": False,
    },
    "team-security-sensitive": {
        "mode": "fresh-strict",
        "coverage_fail_under": 90,
        "change_warn_lines": 150,
        "change_block_files": 10,
        "source_without_test_change_error_profiles": ["precommit", "full", "ci"],
        "suppression_max_new": 0,
        "pyright_type_checking_mode": "strict",
        "ratchet_enabled": False,
        "enable_wemake": True,
    },
}


def test_initializer_presets_write_deterministic_parseable_configs(tmp_path: Path) -> None:
    """Each onboarding preset writes deterministic starter config."""

    for preset, expected_values in PRESET_EXPECTATIONS.items():
        first_target = tmp_path / f"{preset}-first"
        second_target = tmp_path / f"{preset}-second"
        assert initializer.main(["--target", str(first_target), "--preset", preset]) == 0
        assert initializer.main(["--target", str(second_target), "--preset", preset]) == 0

        first_config = (first_target / STARTER_CONFIG).read_text(encoding="utf-8")
        second_config = (second_target / STARTER_CONFIG).read_text(encoding="utf-8")
        parsed = tomllib.loads(first_config)
        config = parsed["tool"]["agent_maintainer"]

        assert first_config == second_config
        assert f"# Onboarding preset: {preset}." in first_config
        for key, expected in expected_values.items():
            assert config[key] == expected


def test_initializer_default_preset_matches_existing_app(tmp_path: Path) -> None:
    """No-preset init keeps existing app starter behavior."""

    default_target = tmp_path / "default"
    explicit_target = tmp_path / "explicit"
    assert initializer.main(["--target", str(default_target)]) == 0
    assert initializer.main(["--target", str(explicit_target), "--preset", "existing-app"]) == 0

    default_config = (default_target / STARTER_CONFIG).read_text(encoding="utf-8")
    explicit_config = (explicit_target / STARTER_CONFIG).read_text(encoding="utf-8")
    assert default_config == explicit_config


def test_initializer_preset_preserves_track_file_selection(tmp_path: Path) -> None:
    """Preset tunes config while track still controls generated files."""

    status = initializer.main(
        [
            "--target",
            str(tmp_path),
            "--track",
            "agent",
            "--preset",
            "ai-agent-heavy",
        ],
    )

    assert status == 0
    assert (tmp_path / STARTER_CONFIG).exists()
    assert (tmp_path / ".codex" / "hooks" / "stop_full_verify.py").exists()
    assert (tmp_path / ".claude" / "hooks" / "stop.py").exists()
    assert not (tmp_path / "package.json").exists()
    config = tomllib.loads((tmp_path / STARTER_CONFIG).read_text(encoding="utf-8"))
    assert config["tool"]["agent_maintainer"]["mode"] == "fresh-strict"
