"""Tests for public-facing documentation readiness."""

from __future__ import annotations

import re
import subprocess
import tomllib
from pathlib import Path

README = Path("README.md")
MIN_READ_MORE_LINKS = 8

REQUIRED_README_LINKS = (
    "docs/quick-start.md",
    "docs/diagnostics-repair-loop.md",
    "docs/agent-client-hooks.md",
    "docs/optional-gates.md",
    "docs/supported-scans-and-agent-use.md",
    "docs/mutation-testing.md",
    "docs/architecture-policy.md",
    "docs/setup-advisor.md",
    "docs/technical-debt-score.md",
    "docs/release-checklist.md",
)


def _project_version() -> str:
    """Return the declared package version."""

    metadata = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    return str(metadata["project"]["version"])


def _version_key(version: str) -> tuple[object, ...]:
    """Sort release evidence versions in human version order."""

    return tuple(int(part) if part.isdigit() else part for part in re.split(r"(\d+)", version))


def _latest_recorded_release_version() -> str:
    """Return the newest recorded release evidence version."""

    release_docs = tuple(Path("docs/releases").glob("*.md"))
    assert release_docs
    return max(release_docs, key=lambda path: _version_key(path.stem)).stem


def _current_release_evidence_version() -> str:
    """Return current package version when recorded, otherwise latest evidence."""

    version = _project_version()
    if Path("docs/releases", f"{version}.md").exists():
        return version
    return _latest_recorded_release_version()


def _commits_since_latest_tag() -> int:
    """Return number of commits after latest release tag, or zero outside Git."""

    latest_tag = subprocess.run(  # nosec B603
        ("git", "describe", "--tags", "--abbrev=0"),
        check=False,
        capture_output=True,
        text=True,
    )
    if latest_tag.returncode != 0:
        return 0

    commit_count = subprocess.run(  # nosec B603
        ("git", "rev-list", "--count", f"{latest_tag.stdout.strip()}..HEAD"),
        check=False,
        capture_output=True,
        text=True,
    )
    if commit_count.returncode != 0:
        return 0
    return int(commit_count.stdout.strip())


def _unreleased_section(changelog: str) -> str:
    """Return the current Unreleased section body."""

    start = changelog.index("## Unreleased")
    next_section = changelog.index("\n## ", start + len("## Unreleased"))
    return changelog[start:next_section]


def test_readme_uses_public_beta_framing() -> None:
    """README starts with package-first beta usage."""
    text = README.read_text(encoding="utf-8")

    visible_text = text.removeprefix(
        "<!-- docsync:object docs.readme.overview -->\n",
    )
    assert visible_text.startswith("# Agent Maintainer\n")
    assert "Agent Maintainer is in beta" in text
    assert 'python -m pip install "agent-maintainer[core]"' in text
    assert "agent-maintainer init --track core" in text
    assert "python3 -m agent_maintainer assess setup" in text
    assert "python3 -m agent_maintainer assess debt" in text
    assert "[Release checklist](docs/release-checklist.md)" in text
    release_version = _current_release_evidence_version()
    assert f"[{release_version} release notes](docs/releases/{release_version}.md)" in text
    assert "[MIT License](LICENSE)" in text
    assert "[Changelog](CHANGELOG.md)" in text
    assert "docs/assets/graphics/agent-maintainer-social-preview.png" in text
    assert "![Python 3.11-3.14]" in text


def test_readme_documents_implemented_assessment_commands() -> None:
    """README should not describe setup advisor or debt score as future-only."""
    text = README.read_text(encoding="utf-8")
    assessment_section = text[text.index("## Setup Recommendations") :]
    assert "Near-term roadmap work will add" not in assessment_section
    assert "Planned work will add" not in assessment_section
    assert "Read proposed design" not in assessment_section


def test_license_and_changelog_are_public_beta_ready() -> None:
    """Release docs expose the public license and initial beta entry."""
    license_text = Path("LICENSE").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert license_text.startswith("MIT License\n")
    assert "Copyright (c) 2026 Doug Monsky" in license_text
    assert f"## {_project_version()}" in changelog
    assert "## 0.1.0b4 - 2026-06-29" in changelog
    assert "Fourth beta release of Agent Maintainer." in changelog
    assert "quiet on success and bounded on failure" in changelog
    assert "## 0.1.0b3 - 2026-06-28" in changelog
    assert "Second beta release of Agent Maintainer." in changelog
    assert "Semgrep is excluded from `manual` and `all` extras" in changelog
    assert "## 0.1.0b1 - 2026-06-27" in changelog
    assert "Initial beta release of Agent Maintainer." in changelog


def test_changelog_unreleased_section_tracks_post_release_commits() -> None:
    """Unreleased changelog must not stay empty after post-tag commits."""

    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    if _commits_since_latest_tag() == 0:
        return

    assert "No changes yet." not in _unreleased_section(changelog)


def test_current_release_docs_match_recorded_evidence() -> None:
    """Current release links should track recorded release evidence."""

    version = _current_release_evidence_version()
    release_path = Path("docs/releases", f"{version}.md")
    readme = README.read_text(encoding="utf-8")
    roadmap = Path("docs/ROADMAP.md").read_text(encoding="utf-8")

    assert release_path.exists()
    assert f"docs/releases/{version}.md" in readme
    assert f"agent-maintainer=={version}" in roadmap
    assert f"`v{version}`" in roadmap
    assert f"docs/releases/{version}.md" in roadmap


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
