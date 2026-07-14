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


def test_skill_covers_every_approved_interaction_scenario() -> None:
    """Client-neutral prose preserves the complete setup decision matrix."""

    bundle = resources.load_bundle()
    skill = next(item for item in bundle.files if item.relative_path == "SKILL.md")

    for scenario, phrases in SCENARIOS.items():
        for phrase in phrases:
            assert phrase in skill.content, f"{scenario} is missing {phrase!r}"
