"""Tests for generated agent guidance."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from agent_maintainer.config.modes import apply_mode
from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.core import guidance as maintainer_guidance


def strict_config() -> MaintainerConfig:
    """Return the same high-level mode this repository uses for itself."""

    return replace(
        apply_mode(MaintainerConfig(), "fresh-strict"),
        architecture_tool="tach",
        source_roots=("src/agent_maintainer", "src/archguard", ".codex/hooks", ".claude/hooks"),
        test_roots=("tests",),
        package_paths=("src/agent_maintainer", "src/archguard", ".codex/hooks", ".claude/hooks"),
        coverage_source=("src/agent_maintainer", "src/archguard", ".codex/hooks", ".claude/hooks"),
        enable_pip_audit=True,
        pip_audit_args=("-r", "config/dev-lock.txt"),
        enable_mutmut=True,
        mutmut_args=("run",),
        enable_semgrep=True,
        semgrep_args=("scan", "--config", "semgrep.yml", "--metrics=off", "."),
        enable_osv_scanner=True,
        osv_scanner_args=("scan", "source", "-r", ".", "--config", "osv-scanner.toml"),
        enable_sbom=True,
        sbom_args=("requirements", "config/dev-lock.txt", "--of", "JSON"),
        enable_license_check=True,
        license_check_args=("--from=mixed", "--format=json"),
        enable_secret_scanning=True,
        secret_scanner="gitleaks",
        secret_scan_profiles=("full", "ci"),
        secret_scan_history_profiles=("security",),
        enable_markdownlint=True,
        markdownlint_paths=("**/*.md",),
        enable_yamllint=True,
        yamllint_paths=(".github/workflows", ".pre-commit-config.yaml"),
        enable_taplo=True,
        taplo_paths=("pyproject.toml", "tach.toml", "osv-scanner.toml"),
        enable_check_jsonschema=True,
        check_jsonschema_args=(
            "--builtin-schema",
            "vendor.github-workflows",
            ".github/workflows/verify.yml",
        ),
    )


def test_render_guidance_includes_active_configuration() -> None:
    text = maintainer_guidance.render_guidance(strict_config())

    assert "Generated Agent Maintainer Guidance" in text
    assert "Details: `docs/agent-maintainer-guidance.md`." in text
    assert "## Hard Rules" in text
    assert "## Context Hygiene" in text
    assert "## Repo Contract" in text
    assert "## Blocking Limits" in text
    assert "## Active Gates" in text
    assert "## Required Commands" in text
    assert "## Optional Gates" not in text
    assert "config/dev-lock.txt" not in text
    assert "semgrep.yml" not in text
    assert "--builtin-schema" not in text
    assert "Keep chat updates summary-first" in text
    assert "Do not emit routine `still running` updates" in text
    assert "Use `apply_patch` for manual edits" in text
    assert "commands for failures" in text
    assert "Expand only if needed" in text
    assert "Mode: `fresh-strict`" in text
    assert (
        "Source roots: `src/agent_maintainer`, `src/archguard`, `.codex/hooks`, `.claude/hooks`"
    ) in text
    assert "Tests: `tests`" in text
    assert "Architecture: `tach` with Tach domain contracts" in text
    assert "Coverage floors: total `80%`, changed `90%`" in text
    assert "Change budget blocks: `600` lines or `12` files" in text
    assert "Source-only changes without test-file changes: `blocked`" in text
    assert "- pip-audit" in text
    assert "- Mutmut" in text
    assert "- Semgrep" in text
    assert "- OSV Scanner" in text
    assert "Trivy" not in text
    assert "- Python SBOM" in text
    assert "- License checking" in text
    assert "- Secret scanning: gitleaks" in text
    assert "- Markdown linting" in text
    assert "- YAML linting" in text
    assert "- TOML formatting" in text
    assert "- Schema validation" in text
    assert "python3 -m agent_maintainer verify --profile precommit" in text
    assert "Before PR/merge: run `full`, `ci`, `security`, and `manual` once" in text
    assert "Structure hint patterns advisory" not in text


def test_render_guidance_is_deterministic_and_nonvolatile() -> None:
    config = strict_config()
    first = maintainer_guidance.render_guidance(config)
    second = maintainer_guidance.render_guidance(config)

    assert first == second
    assert "Generated at" not in first
    assert "git sha" not in first.lower()
    assert str(Path.home()) not in first


def test_render_guidance_changes_when_config_changes() -> None:
    base = strict_config()
    stricter = replace(base, coverage_fail_under=90)

    assert maintainer_guidance.render_guidance(base) != maintainer_guidance.render_guidance(
        stricter
    )
    assert "Coverage floors: total `90%`, changed `90%`" in maintainer_guidance.render_guidance(
        stricter
    )


def test_write_guidance_creates_sidecar(tmp_path: Path) -> None:
    path = maintainer_guidance.write_guidance(tmp_path, strict_config())

    assert path == tmp_path / maintainer_guidance.DEFAULT_GUIDANCE_PATH
    assert path.read_text(encoding="utf-8") == maintainer_guidance.render_guidance(strict_config())


def test_guidance_check_detects_current_missing_and_stale_files(tmp_path: Path) -> None:
    config = strict_config()

    assert maintainer_guidance.guidance_state(tmp_path, config).status == "missing"

    path = tmp_path / maintainer_guidance.DEFAULT_GUIDANCE_PATH
    path.write_text("stale\n", encoding="utf-8")

    assert maintainer_guidance.guidance_state(tmp_path, config).status == "stale"

    maintainer_guidance.write_guidance(tmp_path, config)

    assert maintainer_guidance.guidance_state(tmp_path, config).status == "current"


def test_guidance_main_writes_and_checks_file(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(maintainer_guidance, "load_config", strict_config)

    assert maintainer_guidance.main([]) == 0
    assert "Wrote AGENTS.agent-maintainer.md" in capsys.readouterr().out
    assert maintainer_guidance.main(["--check"]) == 0
    assert "is current" in capsys.readouterr().out

    (tmp_path / maintainer_guidance.DEFAULT_GUIDANCE_PATH).write_text("stale\n", encoding="utf-8")

    assert maintainer_guidance.main(["--check"]) == 1
    assert "is stale" in capsys.readouterr().out
