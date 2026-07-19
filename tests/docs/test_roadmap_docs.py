"""Tests for split roadmap documentation structure."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROADMAP_ROOT = Path("docs/roadmap")
ACTIVE_ROADMAP = Path("docs/ROADMAP.md")
ROADMAP_ARCHIVE = ROADMAP_ROOT / "archive"
ROADMAP_INDEX = ROADMAP_ROOT / "full-roadmap-blueprint.md"
ROADMAP_OVERVIEW = ROADMAP_ROOT / "overview.md"
PHASES_DIR = ROADMAP_ROOT / "phases"
TYPESCRIPT_PARITY_ROADMAP = ROADMAP_ROOT / "typescript-react-parity-roadmap.md"
TYPESCRIPT_PARITY_PHASE = PHASES_DIR / "phase-177-typescript-react-parity-roadmap.md"
TYPESCRIPT_PACKAGE_WORKSPACE_PHASE = (
    PHASES_DIR / "phase-178-advisory-package-manager-workspace-detection.md"
)
TYPESCRIPT_KNIP_PHASE = PHASES_DIR / "phase-179-typescript-knip-unused-code-dependency-facts.md"
TYPESCRIPT_DEPENDENCY_CRUISER_PHASE = (
    PHASES_DIR / "phase-181-typescript-dependency-cruiser-facts.md"
)
CPP_CMAKE_ROADMAP = ROADMAP_ROOT / "cpp-cmake-experimental-provider-roadmap.md"
CPP_PHASE_PATHS = tuple(
    PHASES_DIR / filename
    for filename in (
        "phase-186-cpp-provider-contract-and-roadmap.md",
        "phase-187-cpp-classification-config-registry-doctor.md",
        "phase-188-cpp-explicit-commands-and-bounded-artifacts.md",
        "phase-189-cpp-static-analysis-facts.md",
        "phase-190-cpp-test-and-coverage-facts.md",
        "phase-191-cpp-cross-platform-and-external-proof.md",
    )
)
MAX_ACTIVE_ROADMAP_LINES = 180
MAX_INDEX_OVERHEAD_LINES = 4
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

    phase_paths = sorted(PHASES_DIR.glob("phase-*.md"))
    assert len(lines) <= len(phase_paths) + MAX_INDEX_OVERHEAD_LINES
    assert "Do not re-expand index into monolithic blueprint." in normalized_text
    assert "(overview.md)" in text
    for phase_path in phase_paths:
        assert f"(phases/{phase_path.name})" in text, phase_path.name

    for target in markdown_links(text):
        assert (ROADMAP_ROOT / target).exists(), target


def tracked_completed_phase_archives() -> tuple[Path, ...]:
    """Return completed phase archive files tracked by Git."""

    result = subprocess.run(
        [
            "git",
            "ls-files",
            "docs/roadmap/archive/completed-phases-*.md",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return tuple(Path(path) for path in sorted(result.stdout.splitlines()))


def test_active_roadmap_stays_small_and_links_archive_buckets() -> None:
    """Active roadmap stays focused and points to completed-history buckets."""

    text = ACTIVE_ROADMAP.read_text(encoding="utf-8")
    lines = text.splitlines()
    archive_text = (ROADMAP_ARCHIVE / "README.md").read_text(encoding="utf-8")

    assert len(lines) <= MAX_ACTIVE_ROADMAP_LINES
    assert "Completed Phase Archive" in text
    assert "Phase 149: DocSync Verifier Integration Repair Facts" in text
    assert "## Completed: DocSync Foundation" not in text
    for bucket in tracked_completed_phase_archives():
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


def test_typescript_parity_roadmap_keeps_execution_explicit_and_phased() -> None:
    """Parity planning stays advisory, evidence-backed, and independently merged."""

    roadmap = TYPESCRIPT_PARITY_ROADMAP.read_text(encoding="utf-8")
    phase = TYPESCRIPT_PARITY_PHASE.read_text(encoding="utf-8")
    normalized_roadmap = " ".join(roadmap.split())

    for phrase in (
        "focused pull requests to `main`",
        "Phase 178: advisory package-manager and workspace detection is complete.",
        "Phase 179: Knip unused-code and dependency facts are complete.",
        "Phase 180: OSV dependency facts are complete.",
        "Phase 181: dependency-cruiser architecture-boundary facts are complete.",
        "Package-manager audit facts are the next parity slice.",
        "Repository evidence must never become subprocess arguments.",
        "at least two external real-repository comparisons",
        "TypeScript/React blocking-gate promotion assessment",
    ):
        assert phrase in normalized_roadmap
    assert phase.startswith("# Phase 177: TypeScript/React Parity Roadmap")
    assert "Status: complete" in phase
    assert "No provider runtime behavior changes." in phase


def test_typescript_package_workspace_phase_is_complete_and_advisory() -> None:
    """Phase 178 records the delivered evidence and preserves command ownership."""
    phase = TYPESCRIPT_PACKAGE_WORKSPACE_PHASE.read_text(encoding="utf-8")
    assert phase.startswith("# Phase 178: Advisory Package-Manager And Workspace Detection")
    assert "Status: complete" in phase
    assert "No inferred command execution" in phase
    assert "Knip unused-code and dependency facts" in phase


def test_typescript_knip_phase_is_complete_and_bounded() -> None:
    """Phase 179 records explicit commands, parser bounds, and public evidence."""

    phase = TYPESCRIPT_KNIP_PHASE.read_text(encoding="utf-8")

    assert phase.startswith("# Phase 179: TypeScript Knip Unused-Code And Dependency Facts")
    assert "Status: complete" in phase
    assert "typescript_knip_command" in phase
    assert "500 normalized findings" in phase
    assert "50 total lines" in phase
    assert "TanStack Query" in phase
    assert "Astro" in phase
    assert "TypeScript/JavaScript remains experimental" in phase
    assert "OSV dependency scanning" in phase


def test_typescript_dependency_cruiser_phase_is_complete() -> None:
    """Phase 181 records the advisory architecture boundary and evidence."""

    phase = TYPESCRIPT_DEPENDENCY_CRUISER_PHASE.read_text(encoding="utf-8")

    assert phase.startswith("# Phase 181: TypeScript Dependency-Cruiser Facts")
    assert "Status: complete" in phase
    assert "typescript_dependency_cruiser_command" in phase
    assert "summary.violations" in phase
    assert "500 normalized findings" in phase
    assert "50 total lines" in phase
    assert "decentralized-identity/dwn-sdk-js" in phase
    assert "hicommonwealth/commonwealth" in phase
    assert "TypeScript/JavaScript remains experimental" in phase
    assert "Package-manager audit facts are the next parity slice" in phase


def test_cpp_cmake_experiment_is_explicit_cross_platform_and_phased() -> None:
    """C/C++ planning stays command-owned, cross-platform, and experimental."""

    roadmap = CPP_CMAKE_ROADMAP.read_text(encoding="utf-8")
    normalized = " ".join(roadmap.split())

    for phrase in (
        "disabled by default",
        "repository-owned explicit commands",
        "Linux/GCC",
        "macOS/Clang",
        "Windows/MSVC",
        "Clang-Tidy exported-fixes YAML",
        "Cppcheck XML version 2",
        "CTest JUnit XML",
        "LCOV tracefiles",
        "version-declared gcovr JSON",
        "three pinned public repositories",
    ):
        assert phrase in normalized
    assert "does not select a compiler" in normalized
    assert [path.exists() for path in CPP_PHASE_PATHS] == [True] * 6
    assert "Status: complete" in CPP_PHASE_PATHS[0].read_text(encoding="utf-8")
    for phase in CPP_PHASE_PATHS[1:]:
        assert "Status: planned" in phase.read_text(encoding="utf-8")
    for target in markdown_links(roadmap):
        assert (ROADMAP_ROOT / target).exists(), target


def test_active_roadmap_reports_current_strict_and_api_state() -> None:
    """The active tracker does not revive completed strict-typing debt."""

    text = Path("docs/ROADMAP.md").read_text(encoding="utf-8")

    assert "`1,265` diagnostics" not in text
    assert "Strict Pyright cutover complete" in text
    assert "[x] Reclassify top-level help" in text
    assert "[x] Add `agent_waits`" in text
    assert "[x] Publish exact-installed-version expectations" in text
    assert "[x] Guarantee changed, failed, exact-fact" in text
    assert "[x] Validate attention schema version" in text
    assert "Phase 176: Codex Terminal Rewake Hardening" in text
    assert "Phase 177: TypeScript/React Parity Roadmap" in text
    assert "Phase 178: Advisory Package-Manager And Workspace Detection" in text
    assert "Phase 179: TypeScript Knip Unused-Code And Dependency Facts" in text
    assert "Phase 181: TypeScript Dependency-Cruiser Facts" in text
    assert "(roadmap/typescript-react-parity-roadmap.md)" in text


def test_phase_specs_are_split_and_bounded() -> None:
    """Detailed phase specs live in bounded per-phase files."""

    phase_paths = sorted(PHASES_DIR.glob("phase-*.md"))

    assert len(phase_paths) >= MIN_PHASE_FILES
    assert all(path.read_text(encoding="utf-8").startswith("# Phase ") for path in phase_paths)
    for path in phase_paths:
        assert len(path.read_text(encoding="utf-8").splitlines()) <= MAX_PHASE_LINES, path
