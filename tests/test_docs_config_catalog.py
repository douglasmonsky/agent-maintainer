"""Tests documentation and config hygiene check catalog construction."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ai_guardrails.catalogs import docs as guardrail_catalog_docs
from ai_guardrails.core.config import GuardrailConfig


def test_docs_config_hygiene_commands_follow_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text("# Guide\n", encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "verify.yml").write_text(
        "name: verify\n", encoding="utf-8"
    )
    (tmp_path / "pyproject.toml").write_text("[tool.example]\n", encoding="utf-8")
    disabled = GuardrailConfig()
    enabled = replace(
        GuardrailConfig(),
        enable_markdownlint=True,
        markdownlint_paths=("docs/**/*.md",),
        enable_yamllint=True,
        yamllint_paths=(".github/workflows",),
        enable_taplo=True,
        taplo_paths=("pyproject.toml",),
        enable_check_jsonschema=True,
        check_jsonschema_args=(
            "--builtin-schema",
            "vendor.github-workflows",
            ".github/workflows/verify.yml",
        ),
    )

    assert guardrail_catalog_docs.markdownlint_check(disabled).optional_skip_reason
    assert guardrail_catalog_docs.markdownlint_check(enabled).command == [
        "markdownlint-cli2",
        "docs/guide.md",
    ]
    assert guardrail_catalog_docs.yamllint_check(enabled).command == [
        "yamllint",
        ".github/workflows",
    ]
    assert guardrail_catalog_docs.taplo_check(enabled).command == [
        "taplo",
        "fmt",
        "--check",
        "pyproject.toml",
    ]
    assert guardrail_catalog_docs.check_jsonschema_check(enabled).command == [
        "check-jsonschema",
        "--builtin-schema",
        "vendor.github-workflows",
        ".github/workflows/verify.yml",
    ]


def test_docs_config_hygiene_skips_when_enabled_without_matching_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    config = replace(
        GuardrailConfig(),
        enable_markdownlint=True,
        markdownlint_paths=("docs/**/*.md",),
        enable_yamllint=True,
        yamllint_paths=("*.yaml",),
        enable_taplo=True,
        taplo_paths=("*.toml",),
    )

    markdown_reason = guardrail_catalog_docs.markdownlint_check(config).optional_skip_reason
    yaml_reason = guardrail_catalog_docs.yamllint_check(config).optional_skip_reason
    toml_reason = guardrail_catalog_docs.taplo_check(config).optional_skip_reason

    assert markdown_reason is not None
    assert yaml_reason is not None
    assert toml_reason is not None
    assert "no Markdown files" in markdown_reason
    assert "no YAML files" in yaml_reason
    assert "no TOML files" in toml_reason


def test_matching_paths_ignores_generated_dependency_folders(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "README.md").write_text("# Readme\n", encoding="utf-8")
    dependency_docs = tmp_path / "node_modules" / "pkg"
    dependency_docs.mkdir(parents=True)
    (dependency_docs / "README.md").write_text("# Dependency\n", encoding="utf-8")

    assert guardrail_catalog_docs.matching_paths(("**/*.md",)) == ("README.md",)
