"""Tests for public-facing documentation readiness."""

from __future__ import annotations

from pathlib import Path

README = Path("README.md")


def test_readme_uses_public_beta_framing() -> None:
    """README starts with package-first beta usage."""
    text = README.read_text(encoding="utf-8")

    assert text.startswith("# Agent Maintainer\n")
    assert "Agent Maintainer is in beta" in text
    assert 'python -m pip install "agent-maintainer[core]"' in text
    assert "agent-maintainer init --track core" in text
    assert "[Release checklist](docs/release-checklist.md)" in text
    assert "[MIT License](LICENSE)" in text
    assert "[Changelog](CHANGELOG.md)" in text


def test_license_and_changelog_are_public_beta_ready() -> None:
    """Release docs expose the public license and initial beta entry."""
    license_text = Path("LICENSE").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert license_text.startswith("MIT License\n")
    assert "Copyright (c) 2026 Doug Monsky" in license_text
    assert "## 0.1.0b2 - 2026-06-27" in changelog
    assert "Second beta release of Agent Maintainer." in changelog
    assert "Semgrep is excluded from `manual` and `all` extras" in changelog
    assert "## 0.1.0b1 - 2026-06-27" in changelog
    assert "Initial beta release of Agent Maintainer." in changelog


def test_readme_omits_private_history_terms() -> None:
    """README avoids private-history and old-identity wording."""
    forbidden = [
        "Why Not Call This " + "Guard" + "rails",
        "Legacy " + "Vendored Install",
        "ai_" + "guard" + "rails",
        "ai-" + "guard" + "rails",
        "[tool." + "ai_" + "guard" + "rails]",
        "AGENTS." + "guard" + "rails.md",
    ]
    text = README.read_text(encoding="utf-8")

    offenders = [fragment for fragment in forbidden if fragment in text]
    assert offenders == []
