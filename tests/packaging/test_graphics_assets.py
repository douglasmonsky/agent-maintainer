"""Tests for README graphics documentation assets."""

from __future__ import annotations

from pathlib import Path

GRAPHICS = Path("docs/assets/graphics")
README = Path("README.md")
TOOL_MAP = Path("docs/tool-map.md")


def test_graphics_sources_exist() -> None:
    """Editable graphics sources and rendered PNGs are committed."""

    expected = [
        "overview.html",
        "standard-runs.html",
        "style.css",
        "symbols.svg",
        "render_graphics.py",
        "requirements.txt",
        "agent-maintainer-overview.png",
        "agent-maintainer-social-preview.png",
        "standard-runs-at-a-glance.png",
    ]

    missing = [name for name in expected if not (GRAPHICS / name).exists()]

    assert missing == []


def test_graphics_do_not_use_old_identity_terms() -> None:
    """Graphics sources should not reintroduce pre-rename product identity."""

    forbidden = [
        "ai_" + "guard" + "rails",
        "ai-" + "guard" + "rails",
        "[tool." + "ai_" + "guard" + "rails]",
        "AGENTS." + "guard" + "rails.md",
        "Core " + "Guard" + "rails",
        "Why Not Call This " + "Guard" + "rails",
        "Legacy " + "Vendored Install",
    ]
    offenders: list[str] = []

    for path in GRAPHICS.rglob("*"):
        if path.suffix not in {".html", ".css", ".svg", ".py", ".md"}:
            continue
        text = path.read_text(encoding="utf-8")
        for fragment in forbidden:
            if fragment in text:
                offenders.append(f"{path.as_posix()}: {fragment}")

    assert offenders == []


def test_readme_embeds_hero_graphic() -> None:
    """README includes top-level hero graphic and searchable docs remain intact."""

    text = README.read_text(encoding="utf-8")

    assert "docs/assets/graphics/agent-maintainer-social-preview.png" in text
    assert "Make AI agents edit better" in text
    assert "## Quick Start" in text


def test_tool_map_embeds_standard_runs_graphic() -> None:
    """Tool map includes detailed standard-runs graphic."""

    text = TOOL_MAP.read_text(encoding="utf-8")

    assert "assets/graphics/standard-runs-at-a-glance.png" in text
    assert "Agent Maintainer standard runs comparison" in text
