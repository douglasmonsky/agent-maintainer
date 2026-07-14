"""Tests for the packaged cross-client Agent Maintainer setup skill."""

from __future__ import annotations

from agent_maintainer.skill import resources

SHA256_HEX_LENGTH = 64


def test_shared_skill_has_portable_frontmatter_and_setup_modes() -> None:
    """One common skill triggers before initial commits in both clients."""

    bundle = resources.load_bundle()
    skill = next(item for item in bundle.files if item.relative_path == "SKILL.md")

    assert bundle.name == "agent-maintainer-setup"
    assert skill.content.startswith("---\nname: agent-maintainer-setup\ndescription: ")
    assert "disable-model-invocation" not in skill.content
    assert "allowed-tools" not in skill.content
    assert "creating, scaffolding, bootstrapping, or initializing" in skill.content
    assert "Set up Agent Maintainer for this repository?" in skill.content
    assert skill.content.count("**Recommended**") == 1
    assert skill.content.count("**Guided**") == 1
    assert skill.content.count("**Full control**") == 1
    assert "before the initial commit" in skill.content
    assert "Do not add an MCP server or compatibility shim." in skill.content


def test_shared_skill_covers_approved_setup_pipeline() -> None:
    """The portable instructions retain every approved setup boundary."""

    bundle = resources.load_bundle()
    skill = next(item for item in bundle.files if item.relative_path == "SKILL.md")

    expected_phrases = (
        "track `agent` and preset `strict-new-repo`",
        "agent-maintainer assess setup --target",
        "agent-maintainer init",
        "--dry-run",
        "AGENTS.agent-maintainer.md",
        "agent-maintainer doctor",
        "agent-maintainer verify --profile precommit",
        ".agent-maintainer/tool-requirements.txt",
        ".agent-maintainer/venv/",
        "Leave the repository uncommitted when setup verification fails.",
    )
    for phrase in expected_phrases:
        assert phrase in skill.content


def test_codex_metadata_names_the_shared_skill() -> None:
    """Codex UI metadata remains optional supporting content for Claude."""

    bundle = resources.load_bundle()
    metadata = next(item for item in bundle.files if item.relative_path == "agents/openai.yaml")

    assert 'display_name: "Agent Maintainer Setup"' in metadata.content
    assert (
        'short_description: "Configure new repositories with Agent Maintainer"' in metadata.content
    )
    assert "$agent-maintainer-setup" in metadata.content


def test_resource_digests_match_utf8_content() -> None:
    """Lifecycle ownership can trust deterministic packaged digests."""

    bundle = resources.load_bundle()

    assert {item.relative_path for item in bundle.files} == {
        "SKILL.md",
        "agents/openai.yaml",
    }
    assert all(len(item.digest) == SHA256_HEX_LENGTH for item in bundle.files)
