"""Tests for GitHub Actions hardening policy files."""

from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    """Return the repository root for file policy tests."""

    return Path(__file__).resolve().parents[1]


def test_verify_workflow_declares_read_only_contents_permission() -> None:
    workflow = (repo_root() / ".github" / "workflows" / "verify.yml").read_text(encoding="utf-8")

    assert "\npermissions:\n  contents: read\n" in workflow


def test_dependabot_updates_tag_pinned_github_actions() -> None:
    dependabot = (repo_root() / ".github" / "dependabot.yml").read_text(encoding="utf-8")

    assert 'package-ecosystem: "github-actions"' in dependabot
    assert 'directory: "/"' in dependabot
    assert 'interval: "weekly"' in dependabot
