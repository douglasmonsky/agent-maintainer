"""Tests for split roadmap documentation structure."""

from __future__ import annotations

import re
from pathlib import Path

ROADMAP_ROOT = Path("docs/roadmap")
ACTIVE_ROADMAP = Path("docs/ROADMAP.md")
ROADMAP_ARCHIVE = ROADMAP_ROOT / "archive"
ROADMAP_INDEX = ROADMAP_ROOT / "full-roadmap-blueprint.md"
ROADMAP_OVERVIEW = ROADMAP_ROOT / "overview.md"
PHASES_DIR = ROADMAP_ROOT / "phases"
MAX_ACTIVE_ROADMAP_LINES = 180
MAX_INDEX_LINES = 160
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
    assert "Do not re-expand index into monolithic blueprint." in normalized_text
    assert "(overview.md)" in text
    phase_paths = sorted(PHASES_DIR.glob("phase-*.md"))
    for phase_path in phase_paths:
        assert f"(phases/{phase_path.name})" in text, phase_path.name

    for target in markdown_links(text):
        assert (ROADMAP_ROOT / target).exists(), target


def test_active_roadmap_stays_small_and_links_archive_buckets() -> None:
    """Active roadmap stays focused and points to completed-history buckets."""

    text = ACTIVE_ROADMAP.read_text(encoding="utf-8")
    lines = text.splitlines()
    archive_text = (ROADMAP_ARCHIVE / "README.md").read_text(encoding="utf-8")

    assert len(lines) <= MAX_ACTIVE_ROADMAP_LINES
    assert "Completed Phase Archive" in text
    assert "Phase 149: DocSync Verifier Integration Repair Facts" in text
    assert "## Completed: DocSync Foundation" not in text
    for bucket in sorted(ROADMAP_ARCHIVE.glob("completed-phases-*.md")):
        assert f"(roadmap/archive/{bucket.name})" in text, bucket.name
        assert f"({bucket.name})" in archive_text, bucket.name


def test_roadmap_overview_describes_current_state() -> None:
    """Roadmap overview stays oriented to current product state."""

    text = ROADMAP_OVERVIEW.read_text(encoding="utf-8")
    normalized_text = " ".join(text.split())

    assert "current-state roadmap overview" in text
    assert "Python is the core/reference provider." in text
    assert "TypeScript/JavaScript is experimental" in text
    assert "next major product layer" not in normalized_text
    assert "Master implementation blueprint" not in normalized_text


def test_phase_specs_are_split_and_bounded() -> None:
    """Detailed phase specs live in bounded per-phase files."""

    phase_paths = sorted(PHASES_DIR.glob("phase-*.md"))

    assert len(phase_paths) >= MIN_PHASE_FILES
    assert all(path.read_text(encoding="utf-8").startswith("# Phase ") for path in phase_paths)
    for path in phase_paths:
        assert len(path.read_text(encoding="utf-8").splitlines()) <= MAX_PHASE_LINES, path
