"""Tests for the setup skill's deterministic interaction contract."""

from __future__ import annotations

from agent_maintainer.skill import resources

SCENARIOS = {
    "decline": (
        "make no Agent Maintainer changes",
        "do not ask again",
    ),
    "recommended_python": (
        "track `agent`",
        "preset `strict-new-repo`",
    ),
    "typescript": (
        "Do not guess",
        "explicit TypeScript command",
    ),
    "escalation": ("continue in Guided or Full control",),
    "guided": (
        "Ask only questions",
        "materially affect this repository",
    ),
    "full_control": (
        "every supported",
        "before writing repository files",
    ),
    "completion": (
        "Merge",
        "agent-maintainer doctor",
        "--profile precommit",
    ),
}

MODE_RENDERING_DIRECTIVE = (
    "present the following three choices using exactly these words and punctuation. "
    "Do not paraphrase, summarize, reorder, restyle, or add emphasis:"
)


def test_skill_covers_every_approved_interaction_scenario() -> None:
    """Client-neutral prose preserves the complete setup decision matrix."""

    bundle = resources.load_bundle()
    skill = next(item for item in bundle.files if item.relative_path == "SKILL.md")

    for scenario, phrases in SCENARIOS.items():
        for phrase in phrases:
            assert phrase in skill.content, f"{scenario} is missing {phrase!r}"


def test_skill_requires_verbatim_mode_descriptions() -> None:
    """Live clients must not compress the approved choice descriptions."""
    bundle = resources.load_bundle()
    skill = next(item for item in bundle.files if item.relative_path == "SKILL.md")

    assert MODE_RENDERING_DIRECTIVE in " ".join(skill.content.split())
