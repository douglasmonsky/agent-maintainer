"""Tests for GitHub Actions hardening policy files."""

from __future__ import annotations

from tests.support.paths import REPO_ROOT

DEEP_VERIFY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deep-verify.yml"
VERIFY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "verify.yml"


def test_verify_workflow_declares_read_only_contents_permission() -> None:
    workflow = VERIFY_WORKFLOW.read_text(encoding="utf-8")

    assert "\npermissions:\n  contents: read\n" in workflow


def test_checkout_does_not_persist_credentials() -> None:
    workflow = VERIFY_WORKFLOW.read_text(encoding="utf-8")

    assert "persist-credentials: false" in workflow


def test_verify_workflow_disables_python_bytecode_writes() -> None:
    workflow = VERIFY_WORKFLOW.read_text(encoding="utf-8")

    assert 'PYTHONDONTWRITEBYTECODE: "1"' in workflow


def test_verify_workflow_installs_gitleaks_from_release_artifact() -> None:
    workflow = VERIFY_WORKFLOW.read_text(encoding="utf-8")

    assert "GITLEAKS_VERSION=8.30.1" in workflow
    assert "GITLEAKS_SHA256=" in workflow
    assert "sha256sum" in workflow
    assert 'test "$ACTUAL_SHA256" = "$GITLEAKS_SHA256"' in workflow
    assert "github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}" in workflow
    assert "gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" in workflow
    assert "go install github.com/gitleaks/gitleaks" not in workflow


def test_verify_workflow_installs_node_backed_external_tools() -> None:
    workflow = VERIFY_WORKFLOW.read_text(encoding="utf-8")

    assert "npm ci" in workflow
    assert "npm install -g" not in workflow


def test_deep_verify_workflow_runs_scheduled_manual_security_profiles() -> None:
    """Slow profiles have an automated cadence outside normal PR CI."""
    workflow = DEEP_VERIFY_WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "schedule:" in workflow
    assert "python3 -m agent_maintainer verify --profile security" in workflow
    assert "python3 -m agent_maintainer verify --profile manual" in workflow
    assert "\npermissions:\n  contents: read\n" in workflow
    assert "persist-credentials: false" in workflow
    assert 'PYTHONDONTWRITEBYTECODE: "1"' in workflow


def test_deep_verify_workflow_installs_required_external_tools() -> None:
    """Scheduled deep checks install external binaries they dogfood."""
    workflow = DEEP_VERIFY_WORKFLOW.read_text(encoding="utf-8")

    assert "npm ci" in workflow
    assert "GITLEAKS_VERSION=8.30.1" in workflow
    assert "OSV_SCANNER_VERSION=2.4.0" in workflow
    assert "sha256sum" in workflow
    assert "python -m pip install -e ." in workflow


def test_dependabot_updates_tag_pinned_github_actions() -> None:
    dependabot = (REPO_ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")

    assert 'package-ecosystem: "github-actions"' in dependabot
    assert 'directory: "/"' in dependabot
    assert 'interval: "weekly"' in dependabot
    assert "default-days: 7" in dependabot


def test_zizmor_config_matches_tag_pinning_policy() -> None:
    config = (REPO_ROOT / "zizmor.yml").read_text(encoding="utf-8")

    assert "unpinned-uses:" in config
    assert "actions/*: ref-pin" in config
