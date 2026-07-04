"""Regression tests for first-touch public and agent guidance prose."""

from __future__ import annotations

from pathlib import Path


def normalized_text(path: str) -> str:
    """Return Markdown text with whitespace normalized for phrase checks."""
    return " ".join(Path(path).read_text(encoding="utf-8").split())


def test_agent_guidance_contains_full_operational_phrases() -> None:
    """Agent-facing docs must not regress into compressed note fragments."""
    phrases = {
        "AGENTS.md": (
            "the goal is maintainable code, not just passing code.",
            "It is generated from `[tool.agent_maintainer]`",
            "If hooks are unavailable, bypassed, or need a failure reproduced manually, run:",
            "Do not duplicate a same-state hook pass manually.",
            "Before opening or merging a larger change, run one broad local profile",
            "Do not claim completion while required hooks or manual checks fail.",
            "Keep Python files below 600 physical lines and 450 source lines.",
            "Changed code should be covered by tests; CI enforces changed-code coverage.",
        ),
        "AGENTS.agent-maintainer.md": (
            "Do not edit by hand.",
            "Do not emit routine `still running` updates for expected long checks.",
            "Use `apply_patch` for manual edits; avoid heredoc rewrite commands.",
            "do not duplicate a same-state hook pass manually.",
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
    _assert_phrases_present(phrases)


def test_public_docs_contain_clear_onboarding_phrases() -> None:
    """README and quick start preserve package-first beta wording."""
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
            "For source-checkout development on Agent Maintainer itself, use an "
            "editable install instead:",
            "Run the initializer from the target repository:",
            "A healthy verification run is intentionally quiet:",
            "If verification fails, inspect the bounded repair note first:",
            "a later hook run does not overwrite details needed to repair the failure.",
        ),
    }
    _assert_phrases_present(phrases)


# docsync:evidence.start evidence.typescript.provider_docs_maturity_tests
def test_provider_docs_contain_clear_maturity_phrases() -> None:
    """Provider docs must be clear about current maturity and limits."""
    phrases = {
        "docs/provider-status.md": (
            "Agent Maintainer is Python-core today, with an internal provider seam "
            "for careful expansion.",
            "Experimental providers are not feature parity.",
            "There is no active Go provider on `main`.",
            "If a provider abstraction makes an existing Python feature harder "
            "to express, the abstraction is wrong.",
            "Current reviewability gates are globally scheduled but Python-backed.",
            "TypeScript/JavaScript changed files are advisory, but blocking "
            "reviewability policy is not fully multi-ecosystem yet.",
        ),
        "docs/typescript-javascript-provider.md": (
            "It is disabled by default and only runs commands that the repository "
            "configures explicitly.",
            "Agent Maintainer will not guess the package manager or invent a command.",
            "`npm`, `pnpm`, `yarn`, and `bun` are supported only when "
            "the repository supplies exact command arrays.",
            "`Jest`, `Vitest`, `Playwright`, `Cypress`, `Mocha`, and "
            "other runners must be wired through `typescript_test_command`.",
            "`Next.js`, `Vite`, `Astro`, `SvelteKit`, and monorepo "
            "workspace layouts are not inferred into framework specific "
            "default checks, generated-file rules, coverage adapters, "
            "or dependency policies.",
            "Coverage, dependency/security, mutation, and blocking "
            "reviewability adapters are not implemented for "
            "TypeScript/JavaScript yet.",
            "No TypeScript reviewability gate is blocking by default.",
        ),
        "docs/multi-ecosystem-reviewability-policy.md": (
            "Blocking reviewability gates remain Python-backed until "
            "provider-aware policy adapters have fixture and real-repo evidence "
            "that they are low noise.",
            "These summaries are evidence-gathering heuristics.",
            "Do not aggregate TypeScript/JavaScript source changes into the "
            "current blocking change-budget yet.",
        ),
        "docs/case-studies/typescript-provider-maturation.md": (
            "The goal is to learn what should become shared provider "
            "infrastructure without forcing Node-specific assumptions into core.",
            "This closes one maturation gap between patched fixture readers and "
            "real Git diff behavior.",
            "Phase 138 added additional temporary Git repository shapes for "
            "npm, pnpm, Vite, and Vitest.",
            "Phase 139 added one external public-repository comparison against "
            "`vitest-dev/eslint-plugin-vitest`",
            "Phase 140 added a second external comparison from "
            "`jsynowiec/node-typescript-boilerplate`",
            "broader repository samples are still needed before TypeScript "
            "reviewability becomes blocking or supported.",
        ),
    }
    _assert_phrases_present(phrases)


# docsync:evidence.end evidence.typescript.provider_docs_maturity_tests


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
        "provider exists validate ecosystem-provider architecture",
        "Current reviewability gates globally scheduled but Python-backed.",
        "TypeScript/JavaScript changed files advisory, but blocking",
    )
    text = "\n".join(
        Path(path).read_text(encoding="utf-8")
        for path in (
            "AGENTS.md",
            "AGENTS.agent-maintainer.md",
            "README.md",
            "docs/quick-start.md",
            "docs/provider-status.md",
            "docs/typescript-javascript-provider.md",
            "docs/multi-ecosystem-reviewability-policy.md",
            "docs/case-studies/typescript-provider-maturation.md",
            "docs/agent-maintainer-guidance.md",
            "docs/context-safety.md",
            "docs/diagnostics-repair-loop.md",
        )
    )
    for fragment in forbidden_fragments:
        assert fragment not in text


def _assert_phrases_present(phrases: dict[str, tuple[str, ...]]) -> None:
    """Assert each path contains its required prose phrases."""
    for path, expected_phrases in phrases.items():
        text = normalized_text(path)
        missing = [phrase for phrase in expected_phrases if phrase not in text]
        assert not missing, f"{path} missing phrases: {missing!r}"
