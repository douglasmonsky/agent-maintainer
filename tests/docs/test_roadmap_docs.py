"""Tests for split roadmap documentation structure."""

from __future__ import annotations

import re
from pathlib import Path

ROADMAP_ROOT = Path("docs/roadmap")
ROADMAP_INDEX = ROADMAP_ROOT / "full-roadmap-blueprint.md"
PHASES_DIR = ROADMAP_ROOT / "phases"
MAX_INDEX_LINES = 120
MAX_PHASE_LINES = 500
MIN_PHASE_FILES = 50


def markdown_links(text: str) -> tuple[str, ...]:
    """Return local Markdown link targets from text."""

    return tuple(
        match.group("target")
        for match in re.finditer(r"\[[^\]]+\]\((?P<target>[^)#]+)(?:#[^)]+)?\)", text)
        if not match.group("target").startswith(("http://", "https://", "mailto:"))
    )


def test_roadmap_index_stays_small_and_links_split_specs() -> None:
    """Roadmap index points to split specs instead of becoming a monolith."""

    text = ROADMAP_INDEX.read_text(encoding="utf-8")
    normalized_text = " ".join(text.split())
    lines = text.splitlines()

    assert len(lines) <= MAX_INDEX_LINES
    assert "Do not re-expand this index into a monolithic blueprint." in normalized_text
    assert "(overview.md)" in text
    assert "(phases/phase-64-documentation-and-generated-guidance-slimming.md)" in text
    assert "(phases/phase-89-measured-repair-case-studies.md)" in text

    for target in markdown_links(text):
        assert (ROADMAP_ROOT / target).exists(), target


def test_phase_specs_are_split_and_bounded() -> None:
    """Detailed phase specs live in bounded per-phase files."""

    phase_paths = sorted(PHASES_DIR.glob("phase-*.md"))

    assert len(phase_paths) >= MIN_PHASE_FILES
    assert all(path.read_text(encoding="utf-8").startswith("# Phase ") for path in phase_paths)
    for path in phase_paths:
        assert len(path.read_text(encoding="utf-8").splitlines()) <= MAX_PHASE_LINES, path
