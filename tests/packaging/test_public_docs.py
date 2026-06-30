"""Tests for public-facing documentation readiness."""

from __future__ import annotations

from pathlib import Path

README = Path("README.md")
MIN_READ_MORE_LINKS = 8

REQUIRED_README_LINKS = (
    "docs/quick-start.md",
    "docs/diagnostics-repair-loop.md",
    "docs/agent-client-hooks.md",
    "docs/optional-gates.md",
    "docs/mutation-testing.md",
    "docs/architecture-policy.md",
    "docs/release-checklist.md",
)


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
    assert "docs/assets/graphics/agent-maintainer-social-preview.png" in text
    assert "![Python 3.11-3.14]" in text


def test_license_and_changelog_are_public_beta_ready() -> None:
    """Release docs expose the public license and initial beta entry."""
    license_text = Path("LICENSE").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert license_text.startswith("MIT License\n")
    assert "Copyright (c) 2026 Doug Monsky" in license_text
    assert "## 0.1.0b4 - 2026-06-29" in changelog
    assert "Fourth beta release of Agent Maintainer." in changelog
    assert "quiet on success and bounded on failure" in changelog
    assert "## 0.1.0b3 - 2026-06-28" in changelog
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


def test_readme_has_strategic_read_more_links() -> None:
    """README links detailed docs beside the sections that need them."""

    text = README.read_text(encoding="utf-8")

    assert text.count("Read more:") >= MIN_READ_MORE_LINKS
    for link_path in REQUIRED_README_LINKS:
        assert f"]({link_path})" in text
        assert Path(link_path).exists(), link_path
