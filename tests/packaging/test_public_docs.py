"""Tests for public-facing documentation readiness."""

from __future__ import annotations

import re
import subprocess
import tomllib
from pathlib import Path

README = Path("README.md")
API_SUPPORT_POLICY = Path("docs/api-support-policy.md")
COMPATIBILITY_SHIMS = Path("docs/compatibility-shims.md")
RELEASE_INDEX = Path("docs/releases/README.md")
MIN_READ_MORE_LINKS = 8
LATEST_PUBLISHED_LABEL = "Latest published release"
CURRENT_CANDIDATE_LABEL = "Current release candidate"

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


def _indexed_release(label: str) -> tuple[str, str]:
    """Return version and target recorded for a release-index label."""

    index = RELEASE_INDEX.read_text(encoding="utf-8")
    match = re.search(
        rf"^- {re.escape(label)}: \[`([^`]+)`\]\(([^)]+)\)",
        index,
        flags=re.MULTILINE,
    )
    assert match is not None, label
    return match.group(1), match.group(2)


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


def test_public_docs_define_pre_one_api_support() -> None:
    """The beta API promise and shim lifecycle are public and discoverable."""

    readme = README.read_text(encoding="utf-8")
    policy = API_SUPPORT_POLICY.read_text(encoding="utf-8")
    inventory = COMPATIBILITY_SHIMS.read_text(encoding="utf-8")

    assert "docs/api-support-policy.md" in readme
    assert "## Current-version documented surfaces" in policy
    assert "## Current Python entry points" in policy
    assert "no cross-version compatibility guarantee" in policy
    assert "may change or be removed without a deprecation window" in policy
    assert "`docsync.api`" in policy
    assert "not a frozen signature" in policy
    assert "## Deletion rule" in inventory
    assert "Compatibility is not a reason to retain a shim" in inventory
    assert "same tested change" in inventory
    assert "0.1.0b7" not in inventory
    assert "Support window" not in inventory
    assert "Earliest removal" not in inventory
    for group in (
        "Archguard forwarding",
        "Configuration facade",
        "Context extraction",
        "Hook extraction",
        "Repair-fact extraction",
        "Run-artifact extraction",
        "Wait extraction",
    ):
        assert group in inventory

    for source_path in sorted(Path("src").rglob("*.py")):
        source = source_path.read_text(encoding="utf-8")
        if not source.startswith('"""Compatibility'):
            continue
        module = ".".join(source_path.relative_to("src").with_suffix("").parts)
        assert f"`{module}`" in inventory, module


def test_readme_uses_public_beta_framing() -> None:
    """README starts with package-first beta usage."""
    text = README.read_text(encoding="utf-8")

    visible_text = text.removeprefix(
        "<!-- docsync:object docs.readme.overview -->\n",
    )
    assert visible_text.startswith("# Agent Maintainer\n")
    assert "Agent Maintainer is in beta" in text
    published_version, _ = _indexed_release(LATEST_PUBLISHED_LABEL)
    assert f'python -m pip install "agent-maintainer[core]=={published_version}"' in text
    assert f"Latest published package: `agent-maintainer=={published_version}`" in text
    assert f"unpublished `{published_version}` release candidate" not in text
    assert "agent-maintainer==0.1.0b5" not in text
    assert "agent-maintainer init --track core" in text
    assert "python3 -m agent_maintainer assess setup" in text
    assert "python3 -m agent_maintainer assess debt" in text
    assert "[Release checklist](docs/release-checklist.md)" in text
    assert f"docs/releases/{published_version}.md" in text
    assert f"docs/releases/{published_version}.md" in text
    assert "docs/upgrading-to-0.1.0b6.md" in text
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
    assert f"## Unreleased (target: {_project_version()})" in changelog
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

    unreleased = _unreleased_section(changelog)
    assert "No changes yet." not in unreleased
    for required_topic in (
        "repository-controlled filesystem access",
        "managed hook inventory",
        "configuration preflight",
        "runtime events",
        "durable waits",
        "attention ledger",
        "optional MCP",
        "TypeScript/React",
        "exact-commit",
        "SHA-256",
        "DocSync",
    ):
        assert required_topic in unreleased


# docsync:evidence.start evidence.release.public_contract_tests
def test_public_release_docs_record_published_b6_evidence() -> None:
    """Public docs point at published b6 evidence and completed validation."""

    published_version, published_target = _indexed_release(LATEST_PUBLISHED_LABEL)
    published_path = Path("docs/releases", published_target)
    readme = README.read_text(encoding="utf-8")
    roadmap = Path("docs/ROADMAP.md").read_text(encoding="utf-8")
    release = published_path.read_text(encoding="utf-8")

    assert published_version == _project_version()
    assert published_target == f"{published_version}.md"
    assert published_path.exists()
    assert f"docs/releases/{published_version}.md" in readme
    assert f"agent-maintainer=={published_version}" in roadmap
    assert f"`v{published_version}`" in roadmap
    assert f"docs/releases/{published_version}.md" in roadmap
    assert "Phase 176" in roadmap
    assert "real-turn smokes passed" in roadmap
    assert f"# Agent Maintainer {published_version} Release Evidence" in release
    assert "Real-turn smoke: `passed`" in release


def test_published_upgrade_guide_covers_safe_adoption() -> None:
    """Published upgrade guidance installs b6 while retaining safe adoption."""

    published_version, _ = _indexed_release(LATEST_PUBLISHED_LABEL)
    guide_path = Path(f"docs/upgrading-to-{published_version}.md")

    assert guide_path.exists()
    guide = guide_path.read_text(encoding="utf-8")
    assert f"agent-maintainer[core]=={published_version}" in guide
    assert "agent-maintainer init --dry-run" in guide
    assert "agent-maintainer install --dry-run" in guide
    assert "agent-maintainer doctor" in guide
    assert "## Rollback" in guide


# docsync:evidence.end evidence.release.public_contract_tests


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
