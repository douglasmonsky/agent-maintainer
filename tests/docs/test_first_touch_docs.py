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
            "It is the generated `[tool.agent_maintainer]`",
            "If hooks are unavailable, bypassed, or need a failure reproduced manually, run:",
            "same-state hook pass manually.",
            "Before opening or merging a larger change, reach a coherent final state",
            "Do not claim completion while required hooks or checks for the touched surface fail.",
            "Keep Python files below 600 physical lines and 450 source lines.",
            "Changed code should be covered by tests; CI enforces changed-code coverage.",
        ),
        "AGENTS.agent-maintainer.md": (
            "Do not edit by hand.",
            "Do not emit routine `still running` updates for expected long checks.",
            "Use `apply_patch` for manual edits; avoid heredoc rewrite commands.",
            "same-state hook pass manually",
            "After a failed verifier or hook result, read the repair capsule",
            "Prefer run-scoped `context --log-dir ...` commands for failures.",
            "Expand only if needed:",
        ),
        "docs/agent-maintainer-guidance.md": (
            "`AGENTS.agent-maintainer.md` is intentionally compact because agents "
            "load it into working context repeatedly.",
            "Agents should not read it during normal coding unless they are changing "
            "guidance behavior.",
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


def test_setup_skill_docs_preserve_dual_client_consent_contract() -> None:
    """Personal setup guidance keeps timing, modes, and trust boundary explicit."""
    phrases = {
        "docs/agent-maintainer-setup-skill.md": (
            "python -m agent_maintainer skill install --client codex --client claude-code",
            "before the initial commit",
            "Recommended",
            "Guided",
            "Full control",
            "does not add an MCP server",
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
            "format-aware doctor setup and repair-fact output guidance rows.",
            "TypeScript/JavaScript changed files are advisory, but blocking "
            "reviewability policy is not fully multi-ecosystem yet.",
        ),
        "docs/typescript-javascript-provider.md": (
            "It is disabled by default and only runs commands that the repository "
            "configures explicitly.",
            "Agent Maintainer will not guess the package manager or invent a command.",
            "Empty-command doctor hints point to stable output formats",
            "may emit a non-blocking `PASS` advisory row",
            "`npm`, `pnpm`, `yarn`, and `bun` are supported only when "
            "the repository supplies exact command arrays.",
            "`Jest`, `Vitest`, `Playwright`, `Cypress`, `Mocha`, and "
            "other runners must be wired through `typescript_test_command`.",
            "`Next.js`, `Vite`, `Astro`, `SvelteKit`, and monorepo "
            "workspace layouts are not inferred into framework specific "
            "default checks, generated-file rules, coverage commands, "
            "or dependency policies.",
            "Workspace command ownership is explicit.",
            'typescript_knip_command = ["pnpm", "exec", "knip", "--reporter", "json"]',
            "`typescript_knip_profiles` defaults to `full` and `ci`.",
            "Agent Maintainer honors the configured Knip command's exit status",
            "at most 500 normalized findings",
            "at most 50 total lines",
            "Configure root TypeScript commands only when they intentionally "
            "cover packages you want Agent Maintainer to verify.",
            "Agent Maintainer will run only the workspace TypeScript commands "
            "you configure and will not infer nested package commands.",
            "Coverage summaries and LCOV files can improve `typescript-test` repair facts",
            "TypeScript coverage enforcement, dependency security/audit, "
            "mutation, and blocking reviewability adapters are not "
            "implemented yet.",
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
            "workspace command ownership semantics before recursive package discovery",
            "broader repository samples are still needed before TypeScript "
            "reviewability becomes blocking or supported.",
        ),
    }
    _assert_phrases_present(phrases)


# docsync:evidence.end evidence.typescript.provider_docs_maturity_tests


def test_provider_status_tracks_typescript_knip_facts() -> None:
    """Provider status records completed Knip facts and the next parity slice."""
    text = Path("docs/provider-status.md").read_text(encoding="utf-8")
    for expected in (
        "Phase 178 package-manager and workspace evidence is advisory only.",
        "preserves file-and-field provenance",
        "never selects a manager",
        "expands workspace globs",
        "creates a command",
        "Phase 179 Knip unused-code and dependency facts are complete.",
        "TanStack Query",
        "Astro",
        "OSV dependency scanning is the next parity slice",
        "TypeScript/JavaScript remains experimental",
    ):
        assert expected in text


def test_setup_advisor_docs_include_workspace_command_example() -> None:
    """Setup advisor docs keep explicit workspace command ownership concrete."""
    phrases = {
        "docs/setup-advisor.md": (
            "[tool.agent_maintainer.workspaces.web]",
            'typescript_lint_command = ["pnpm", "--filter", "web", "lint"]',
            'typescript_typecheck_command = ["pnpm", "--filter", "web", "typecheck"]',
            'typescript_test_command = ["pnpm", "--filter", "web", "test"]',
            'typescript_knip_command = ["pnpm", "exec", "knip", "--reporter", "json"]',
            (
                'typescript_knip_command = ["pnpm", "--filter", "web", "exec", '
                '"knip", "--reporter", "json"]'
            ),
            "Setup advisor still does not infer nested package commands or workspace managers.",
        ),
    }
    _assert_phrases_present(phrases)


def test_setup_advisor_docs_explain_package_workspace_evidence() -> None:
    """Setup advisor docs explain facts, ambiguity, and explicit ownership."""
    text = Path("docs/setup-advisor.md").read_text(encoding="utf-8")
    for expected in (
        "`packageManager` and `devEngines.packageManager`",
        "`package-lock.json`",
        "`npm-shrinkwrap.json`",
        "`pnpm-lock.yaml`",
        "`yarn.lock`",
        "`bun.lock`",
        "`bun.lockb`",
        "Workspace patterns remain literal and unexpanded.",
        "Detected evidence never becomes a subprocess argument.",
    ):
        assert expected in text


def test_java_setup_docs_pin_native_ratchet_boundaries() -> None:
    """Java setup docs state the reviewed and static safety boundaries."""
    phrases = {
        "docs/provider-status.md": (
            "Spotless `ratchetFrom`",
            "native SpotBugs `FindBugsFilter`",
            "Normal doctor remains static and never executes Gradle.",
            "Java findings baseline lifecycle is explicit",
        ),
        "docs/setup-advisor.md": (
            "Recommended, Guided, or Full control",
            "never regex-rewrites an arbitrary Gradle build",
            "Normal doctor and verification never run `tasks --all`.",
            "preserves existing repository-owned workflows",
        ),
    }

    _assert_phrases_present(phrases)


def test_java_structured_evidence_docs_pin_bounded_lifecycle_contracts() -> None:
    """Public docs describe structured evidence without overstating coverage rollout."""
    phrases = {
        "docs/provider-status.md": (
            "bounded Checkstyle, PMD, SpotBugs, JUnit, and JaCoCo XML evidence",
            "never persists raw Gradle XML",
            "`assess java-baseline create|inspect|prune`",
        ),
        "docs/ratcheting.md": (
            "`assess file-baselines create|inspect|prune`",
            "Renamed paths do not inherit an oversized-file allowance.",
            "Verification is comparison-only",
        ),
        "docs/supported-scans-and-agent-use.md": (
            "provider-neutral per-path file ceilings",
            "complete, non-truncated runner artifacts",
        ),
    }

    _assert_phrases_present(phrases)


def test_codex_wait_docs_disclose_smoke_and_model_turn_boundaries() -> None:
    """Codex wait docs keep diagnostic, fallback, and spend boundaries explicit."""
    phrases = {
        "docs/codex-hooks.md": (
            "heartbeat is a model-turn fallback: each scheduled poll wakes a model",
            "`openai-codex` SDK availability is diagnostic only because no SDK "
            "rewake backend is implemented.",
            "python -m agent_maintainer wait codex-smoke",
            "AGENT_MAINTAINER_CODEX_REWAKE_SMOKE_TURN=1",
            "Never run the real-turn smoke from doctor, hooks, watchers, or CI.",
            "ready_for_manual_resume` -> `notifying` -> `resumed` or `notify_failed",
            "python -m agent_maintainer wait repair --dry-run --stale-after 60",
            "Repair rechecks state under the same per-wait lock, never calls Codex",
            "exponential backoff contract",
            "wait.notify_attempted",
            "They never contain process ids",
        ),
        "docs/agent-client-hooks.md": (
            "Heartbeat fallback still wakes a model each interval",
            "read-only, token-free probe",
            "The `--start-turn` smoke spends one model turn",
            "hooks and CI must never set that gate.",
            "Unconfirmed or failed wake attempts enter manually resumable `notify_failed` state",
            "wait repair --dry-run",
            "cap at 1,800 seconds",
            "Their attributes are allowlisted",
        ),
    }
    _assert_phrases_present(phrases)


def test_known_compressed_prose_fragments_do_not_reappear() -> None:
    """Guard against specific note-fragment regressions found during audit."""
    forbidden_fragments = (
        "Do not edit hand.",
        "Do not emit routine `still running` updates expected long checks.",
        "Use `apply_patch` manual edits;",
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
