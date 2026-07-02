"""Tests scaffold preset policy helpers."""

from __future__ import annotations

from agent_maintainer.core.scaffold import presets

TEAM_TEMPLATE_CASES = (
    (presets.TEAM_SMALL_PYTHON_LIB_PRESET, presets.SMALL_LIBRARY_PRESET),
    (presets.TEAM_LEGACY_SERVICE_PRESET, presets.LEGACY_RATCHET_PRESET),
    (presets.TEAM_AGENT_HEAVY_PRESET, presets.AI_AGENT_HEAVY_PRESET),
    (presets.TEAM_SECURITY_SENSITIVE_PRESET, presets.STRICT_NEW_REPO_PRESET),
)


def test_team_templates_are_public_presets() -> None:
    """Team templates are accepted by initializer preset choices."""
    team_templates = {template for template, _canonical in TEAM_TEMPLATE_CASES}

    assert team_templates.issubset(presets.PRESETS)


def test_team_templates_resolve_to_canonical() -> None:
    """Team templates reuse existing deterministic policy shapes."""
    for template, canonical in TEAM_TEMPLATE_CASES:
        assert presets.aliased_preset(template) == canonical
        assert presets.policy_for(template) == presets.policy_for(canonical)
