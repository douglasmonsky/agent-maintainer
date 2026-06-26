"""Tests for generated agent guidance."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from guardrail_lib.config.modes import apply_mode
from guardrail_lib.config.schema import GuardrailConfig
from scripts import guardrail_guidance


def strict_config() -> GuardrailConfig:
    """Return the same high-level mode this repository uses for itself."""

    return replace(
        apply_mode(GuardrailConfig(), "fresh-strict"),
        architecture_tool="tach",
        source_roots=("scripts", ".codex/hooks"),
        test_roots=("tests",),
        package_paths=("scripts", ".codex/hooks"),
        coverage_source=("scripts", ".codex/hooks"),
        enable_pip_audit=True,
        pip_audit_args=("-r", "config/dev-lock.txt"),
        enable_secret_scanning=True,
        secret_scanner="gitleaks",
        secret_scan_profiles=("full", "ci"),
        secret_scan_history_profiles=("security",),
    )


def test_render_guidance_includes_active_configuration() -> None:
    text = guardrail_guidance.render_guidance(strict_config())

    assert "Generated Guardrail Guidance" in text
    assert "Mode: `fresh-strict`" in text
    assert "Source roots: `scripts`, `.codex/hooks`" in text
    assert "Test roots: `tests`" in text
    assert "Architecture backend: `tach`" in text
    assert "Diagnostic artifacts: `enabled` at `.verify-logs`" in text
    assert "Pyright mode: `standard`" in text
    assert "File length baseline: `disabled`" in text
    assert "Source-without-test-change errors in profiles: `precommit`" in text
    assert "Source-only changes without test-file changes: `blocked`" in text
    assert "pip-audit: enabled with `-r config/dev-lock.txt`" in text
    assert "Secret scanning: enabled with `gitleaks`" in text
    assert "python3 -m scripts.guardrail verify --profile precommit" in text
    assert "Prefer small, coherent commits" in text
    assert "Prefer `rg --files` or `git ls-files`" in text
    assert "`__pycache__`, `*.pyc`, `.venv`" in text
    assert "PYTHONDONTWRITEBYTECODE=1" in text
    assert "Folder Python-file warning/block thresholds" in text
    assert "Structure hint patterns are advisory refactor prompts" in text


def test_render_guidance_is_deterministic_and_nonvolatile() -> None:
    config = strict_config()
    first = guardrail_guidance.render_guidance(config)
    second = guardrail_guidance.render_guidance(config)

    assert first == second
    assert "Generated at" not in first
    assert "git sha" not in first.lower()
    assert str(Path.home()) not in first


def test_render_guidance_changes_when_config_changes() -> None:
    base = strict_config()
    stricter = replace(base, coverage_fail_under=90)

    assert guardrail_guidance.render_guidance(base) != guardrail_guidance.render_guidance(stricter)
    assert "Total coverage floor: `90%`" in guardrail_guidance.render_guidance(stricter)


def test_write_guidance_creates_sidecar(tmp_path: Path) -> None:
    path = guardrail_guidance.write_guidance(tmp_path, strict_config())

    assert path == tmp_path / guardrail_guidance.DEFAULT_GUIDANCE_PATH
    assert path.read_text(encoding="utf-8") == guardrail_guidance.render_guidance(strict_config())


def test_guidance_check_detects_current_missing_and_stale_files(tmp_path: Path) -> None:
    config = strict_config()

    assert guardrail_guidance.guidance_state(tmp_path, config).status == "missing"

    path = tmp_path / guardrail_guidance.DEFAULT_GUIDANCE_PATH
    path.write_text("stale\n", encoding="utf-8")

    assert guardrail_guidance.guidance_state(tmp_path, config).status == "stale"

    guardrail_guidance.write_guidance(tmp_path, config)

    assert guardrail_guidance.guidance_state(tmp_path, config).status == "current"


def test_guidance_main_writes_and_checks_file(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(guardrail_guidance, "load_config", strict_config)

    assert guardrail_guidance.main([]) == 0
    assert "Wrote AGENTS.guardrails.md" in capsys.readouterr().out
    assert guardrail_guidance.main(["--check"]) == 0
    assert "is current" in capsys.readouterr().out

    (tmp_path / guardrail_guidance.DEFAULT_GUIDANCE_PATH).write_text("stale\n", encoding="utf-8")

    assert guardrail_guidance.main(["--check"]) == 1
    assert "is stale" in capsys.readouterr().out
