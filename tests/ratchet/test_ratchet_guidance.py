"""Tests generated ratchet guidance."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from agent_maintainer.config.modes import apply_mode
from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.core import guidance as maintainer_guidance
from agent_maintainer.ratchet.guidance import render_ratchet_guidance


def ratchet_config() -> MaintainerConfig:
    """Return config with ratchet guidance enabled."""

    return replace(
        apply_mode(MaintainerConfig(), "legacy-ratchet"),
        ratchet_enabled=True,
        ratchet_baseline_path=".agent-maintainer/ratchet-baseline.json",
        ratchet_guidance_path="AGENTS.ratchet.md",
        ratchet_target_limit=3,
    )


def test_render_ratchet_guidance_is_deterministic() -> None:
    """Ratchet guidance is deterministic and nonvolatile."""

    config = ratchet_config()
    first = render_ratchet_guidance(config)
    second = render_ratchet_guidance(config)

    assert first == second
    assert "Current mode: `legacy-ratchet`" in first
    assert "Baseline path: `.agent-maintainer/ratchet-baseline.json`" in first
    assert "Top Ratchet Targets" in first
    assert "One Target At A Time" in first
    assert "Safe Context Commands" in first
    assert "context pack --budget" in first
    assert "Change-Plan Warning" in first
    assert "Generated at" not in first


def test_main_guidance_links_ratchet_guidance_when_active() -> None:
    """Main guidance points agents at ratchet guidance when enabled."""

    text = maintainer_guidance.render_guidance(ratchet_config())

    assert "Read `AGENTS.ratchet.md` for legacy ratchet repair guidance." in text


def test_write_guidance_creates_ratchet_sidecar(tmp_path: Path) -> None:
    """Writing guidance creates active ratchet sidecar."""

    config = ratchet_config()

    maintainer_guidance.write_guidance(tmp_path, config)

    ratchet_path = tmp_path / "AGENTS.ratchet.md"
    assert ratchet_path.read_text(encoding="utf-8") == render_ratchet_guidance(config)


def test_guidance_check_detects_stale_ratchet_sidecar(tmp_path: Path) -> None:
    """Guidance check includes ratchet sidecar freshness."""

    config = ratchet_config()
    maintainer_guidance.write_guidance(tmp_path, config)
    ratchet_path = tmp_path / "AGENTS.ratchet.md"
    ratchet_path.write_text("stale\n", encoding="utf-8")

    states = maintainer_guidance.guidance_states(tmp_path, config)

    assert [state.path.as_posix() for state in states] == [
        "AGENTS.agent-maintainer.md",
        "AGENTS.ratchet.md",
    ]
    assert states[0].status == "current"
    assert states[1].status == "stale"
