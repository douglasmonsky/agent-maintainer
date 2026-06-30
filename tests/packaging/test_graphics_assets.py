"""Tests README graphics documentation assets."""

from __future__ import annotations

from pathlib import Path

GRAPHICS = Path("docs/assets/graphics")
README = Path("README.md")
TOOL_MAP = Path("docs/tool-map.md")


def test_static_graphics_assets_exist() -> None:
    """Static public graphics committed without a repo-local render pipeline."""
    expected = [
        "agent-maintainer-overview.png",
        "agent-maintainer-social-preview.png",
        "standard-runs-at-a-glance.png",
    ]
    missing = [name for name in expected if not (GRAPHICS / name).exists()]
    assert missing == []


def test_graphics_render_pipeline_is_not_committed() -> None:
    """Documentation images should not add renderer dependencies to the repo."""
    removed_pipeline_files = [
        "overview.html",
        "standard-runs.html",
        "style.css",
        "symbols.svg",
        "render_graphics.py",
        "requirements.txt",
    ]
    present = [name for name in removed_pipeline_files if (GRAPHICS / name).exists()]
    assert present == []


def test_graphics_do_not_use_old_identity_terms() -> None:
    """Graphics docs should not reintroduce pre-rename product identity."""
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
        if path.suffix not in {".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8")
        for fragment in forbidden:
            if fragment in text:
                offenders.append(f"{path.as_posix()}: {fragment}")
    assert offenders == []


def test_readme_embeds_hero_graphic() -> None:
    """README includes top-level hero graphic searchable docs remain intact."""
    text = README.read_text(encoding="utf-8")
    assert "docs/assets/graphics/agent-maintainer-social-preview.png" in text
    assert "Make AI agents edit better" in text


def test_readme_embeds_runs_graphic() -> None:
    """README includes run profile visual near run profile docs."""
    text = README.read_text(encoding="utf-8")
    assert "docs/assets/graphics/standard-runs-at-a-glance.png" in text
    assert "## Run Profiles" in text
    assert text.index("## Run Profiles") < text.index(
        "docs/assets/graphics/standard-runs-at-a-glance.png",
    )


def test_tool_map_references_runs_graphic() -> None:
    """Tool map embeds standard run graphic for reference docs."""
    text = TOOL_MAP.read_text(encoding="utf-8")
    assert "assets/graphics/standard-runs-at-a-glance.png" in text
