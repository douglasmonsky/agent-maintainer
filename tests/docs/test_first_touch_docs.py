"""Regression tests for first-touch public and agent guidance prose."""

from __future__ import annotations

from pathlib import Path


def normalized_text(path: str) -> str:
    """Return Markdown text with whitespace normalized for phrase checks."""
    return " ".join(Path(path).read_text(encoding="utf-8").split())


def test_agent_guidance_contains_full_operational_phrases() -> None:
    """Agent-facing docs should not regress into compressed note fragments."""
    phrases = {
        "AGENTS.md": (
            "the goal is maintainable code, not just passing code.",
            "It is generated from `[tool.agent_maintainer]`",
            "If hooks are unavailable, bypassed, or need a failure reproduced manually, run:",
            "Before opening or merging a larger change, run:",
            "Do not claim completion while required hooks or manual checks fail.",
            "Keep Python files below 600 physical lines and 450 source lines.",
            "Changed code should be covered by tests; CI enforces changed-code coverage.",
        ),
        "AGENTS.agent-maintainer.md": (
            "Do not edit by hand.",
            "Do not emit routine `still running` updates for expected long checks.",
            "Use `apply_patch` for manual edits; avoid heredoc rewrite commands.",
            "Read `.verify-logs/LAST_FAILURE.md` before changing code or config.",
            "Prefer run-scoped `context --log-dir ...` commands for failures.",
            "Expand only if needed:",
        ),
        "docs/agent-maintainer-guidance.md": (
            "`AGENTS.agent-maintainer.md` is intentionally compact because agents "
            "load it into working context repeatedly.",
            "This document is for humans who want the longer explanation.",
            "Agent Maintainer should reduce repair-loop noise, not become another "
            "source of context waste.",
            'no routine "still running" updates for expected long checks;',
            "Manual source edits should use `apply_patch`.",
            "Do not load full context packs or raw logs unless the capsule is insufficient.",
        ),
    }
    for path, expected_phrases in phrases.items():
        text = normalized_text(path)
        missing = [phrase for phrase in expected_phrases if phrase not in text]
        assert not missing, f"{path} missing phrases: {missing!r}"


def test_public_docs_contain_clear_onboarding_phrases() -> None:
    """README and quick start should preserve package-first beta wording."""
    phrases = {
        "README.md": (
            "Maintainability checks and repair-loop diagnostics for AI-assisted "
            "Python repositories.",
            "Agent Maintainer is in beta.",
            "A healthy verification run is intentionally quiet:",
            "If it fails, read the bounded repair note first:",
            "The note links to run-scoped logs and gives exact expansion/rerun commands.",
        ),
        "docs/quick-start.md": (
            "This is the shortest package-first path for trying Agent Maintainer "
            "in a Python repository.",
            "For source-checkout development of Agent Maintainer itself, use an "
            "editable install instead:",
            "Run the initializer from the target repository:",
            "A healthy verification run is intentionally quiet:",
            "If verification fails, inspect the bounded repair note first:",
            "a later hook run does not overwrite the details needed to repair the failure.",
        ),
        "docs/provider-status.md": (
            "Agent Maintainer is Python-core today, with an internal provider seam "
            "for careful expansion.",
            "Do not read experimental providers as feature parity.",
            "If a provider abstraction makes an existing Python feature harder "
            "to express, the abstraction is wrong.",
            "Current reviewability gates are globally scheduled but Python-backed.",
            "TypeScript/JavaScript changed files are advisory, but blocking "
            "reviewability policy is not fully multi-ecosystem yet.",
        ),
    }
    for path, expected_phrases in phrases.items():
        text = normalized_text(path)
        missing = [phrase for phrase in expected_phrases if phrase not in text]
        assert not missing, f"{path} missing phrases: {missing!r}"


def test_known_compressed_prose_fragments_do_not_reappear() -> None:
    """Guard against specific note-fragment regressions found during audit."""
    forbidden_fragments = (
        "Do not edit hand.",
        "Do not emit routine `still running` updates expected long checks.",
        "Use `apply_patch` manual edits;",
        "Read `.verify-logs/LAST_FAILURE.md` before changing code config.",
        "source-checkout development Agent Maintainer itself, use editable install",
        "Agent Maintainer Python-core today, internal provider seam",
        "Do not read experimental providers feature parity.",
        "Maintainability checks repair-loop diagnostics AI-assisted",
        "Read more where matters:",
        "If fails, read bounded repair note first:",
    )
    text = "\n".join(
        Path(path).read_text(encoding="utf-8")
        for path in (
            "AGENTS.md",
            "AGENTS.agent-maintainer.md",
            "README.md",
            "docs/quick-start.md",
            "docs/provider-status.md",
            "docs/agent-maintainer-guidance.md",
            "docs/context-safety.md",
            "docs/diagnostics-repair-loop.md",
        )
    )
    for fragment in forbidden_fragments:
        assert fragment not in text
