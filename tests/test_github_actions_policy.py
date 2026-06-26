"""Tests for GitHub Actions hardening policy files."""

from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    """Return the repository root for file policy tests."""

    return Path(__file__).resolve().parents[1]


def test_verify_workflow_declares_read_only_contents_permission() -> None:
    workflow = (repo_root() / ".github" / "workflows" / "verify.yml").read_text(encoding="utf-8")

    assert "\npermissions:\n  contents: read\n" in workflow


def test_checkout_does_not_persist_credentials() -> None:
    workflow = (repo_root() / ".github" / "workflows" / "verify.yml").read_text(encoding="utf-8")

    assert "persist-credentials: false" in workflow


def test_verify_workflow_disables_python_bytecode_writes() -> None:
    workflow = (repo_root() / ".github" / "workflows" / "verify.yml").read_text(encoding="utf-8")

    assert 'PYTHONDONTWRITEBYTECODE: "1"' in workflow


def test_verify_workflow_installs_gitleaks_from_release_artifact() -> None:
    workflow = (repo_root() / ".github" / "workflows" / "verify.yml").read_text(encoding="utf-8")

    assert "GITLEAKS_VERSION=8.30.1" in workflow
    assert "GITLEAKS_SHA256=" in workflow
    assert "sha256sum" in workflow
    assert 'test "$ACTUAL_SHA256" = "$GITLEAKS_SHA256"' in workflow
    assert "github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}" in workflow
    assert "gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" in workflow
    assert "go install github.com/gitleaks/gitleaks" not in workflow


def test_verify_workflow_installs_node_backed_external_tools() -> None:
    workflow = (repo_root() / ".github" / "workflows" / "verify.yml").read_text(encoding="utf-8")

    assert "npm ci" in workflow
    assert "npm install -g" not in workflow


def test_dependabot_updates_tag_pinned_github_actions() -> None:
    dependabot = (repo_root() / ".github" / "dependabot.yml").read_text(encoding="utf-8")

    assert 'package-ecosystem: "github-actions"' in dependabot
    assert 'directory: "/"' in dependabot
    assert 'interval: "weekly"' in dependabot
    assert "default-days: 7" in dependabot


def test_zizmor_config_matches_tag_pinning_policy() -> None:
    config = (repo_root() / "zizmor.yml").read_text(encoding="utf-8")

    assert "unpinned-uses:" in config
    assert "actions/*: ref-pin" in config
