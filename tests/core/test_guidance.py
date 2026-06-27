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
        source_roots=("src/agent_maintainer", ".codex/hooks"),
        test_roots=("tests",),
        package_paths=("src/agent_maintainer", ".codex/hooks"),
        coverage_source=("src/agent_maintainer", ".codex/hooks"),
        enable_pip_audit=True,
        pip_audit_args=("-r", "config/dev-lock.txt"),
        enable_mutmut=True,
        mutmut_args=("run",),
        enable_semgrep=True,
        semgrep_args=("scan", "--config", "semgrep.yml", "--metrics=off", "."),
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
        taplo_paths=("pyproject.toml", "tach.toml"),
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
    assert "Mode: `fresh-strict`" in text
    assert "Source roots: `src/agent_maintainer`, `.codex/hooks`" in text
    assert "Test roots: `tests`" in text
    assert "Architecture backend: `tach`" in text
    assert "Diagnostic artifacts: `enabled` at `.verify-logs`" in text
    assert "Pyright mode: `standard`" in text
    assert "File length baseline: `disabled`" in text
    assert "Source-without-test-change errors in profiles: `precommit`" in text
    assert "Source-only changes without test-file changes: `blocked`" in text
    assert "pip-audit: enabled with `-r config/dev-lock.txt`" in text
    assert "Mutmut: enabled with `run`" in text
    assert "Semgrep: enabled with `scan --config semgrep.yml --metrics=off .`" in text
    assert "OSV Scanner: `disabled`" in text
    assert "Trivy: `disabled`" in text
    assert "Python SBOM: enabled with `requirements config/dev-lock.txt --of JSON`" in text
    assert "License checking: enabled with `--from=mixed --format=json`" in text
    assert "Secret scanning: enabled with `gitleaks`" in text
    assert "Markdown linting: enabled with `'**/*.md'`" in text
    assert "YAML linting: enabled with `.github/workflows .pre-commit-config.yaml`" in text
    assert "TOML formatting: enabled with `pyproject.toml tach.toml`" in text
    assert "Schema validation: enabled with `--builtin-schema vendor.github-workflows" in text
    assert "python3 -m agent_maintainer verify --profile precommit" in text
    assert "Prefer small, coherent commits" in text
    assert "Prefer `rg --files` or `git ls-files`" in text
    assert "`__pycache__`, `*.pyc`, `.venv`" in text
    assert "PYTHONDONTWRITEBYTECODE=1" in text
    assert "Folder Python-file warning/block thresholds" in text
    assert "Structure hint patterns are advisory refactor prompts" in text


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
    assert "Total coverage floor: `90%`" in maintainer_guidance.render_guidance(stricter)


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
