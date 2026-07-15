# Roadmap

## Read This First

This file is only the implementation tracker for the Agent Maintainer roadmap.
It is a recovery checklist, not the detailed implementation spec.

Roadmap sources:

- [Detailed spec index](roadmap/full-roadmap-blueprint.md)
- [Split-spec usage guide](roadmap/README.md)
- [Experimental architecture track](roadmap/polyglot-ecosystem-providers.md)

Before implementing any phase:

1. Open [`docs/roadmap/README.md`](roadmap/README.md).
2. Open the roadmap index:
   [`docs/roadmap/full-roadmap-blueprint.md`](roadmap/full-roadmap-blueprint.md).
3. Reopen the matching split phase file under
   [`docs/roadmap/phases/`](roadmap/phases/).
4. Follow the phase's scope, file targets, tests, documentation requirements,
   acceptance criteria, and explicit out-of-scope rules.
5. Use this file only to track phase completion, implementation,
   verification, merge, and post-merge CI confirmation.

Do not infer phase requirements from this checklist alone. If chat context is
compacted or interrupted, resume from the checklist only after reopening the
guide and relevant split phase file. If the split roadmap appears missing or
stale, restore the source document named `agent-maintainer-full-roadmap-blueprint.md`
and split it back into `docs/roadmap/phases/` before continuing implementation.

Agent Maintainer is in beta. The active priorities are proving retained value
in external repositories and paying down reviewed quality debt without
weakening existing gates. Completed feature tracks remain below as recovery
history, not as unstarted plans.

## Current Baseline

The public beta baseline already includes package-first onboarding, verification
profiles, diagnostics, release checks, public packaging metadata, TestPyPI/PyPI
Trusted Publishing workflow, Codex and Claude Code hooks, generated guidance,
example repos, and the first cohesive-change budget exception.

Current external release state:

- [x] `agent-maintainer==0.1.0b6` is published to TestPyPI and PyPI,
      attached to GitHub prerelease `v0.1.0b6`, and smoke-tested from both
      package indexes. Release evidence is recorded in
      [`docs/releases/0.1.0b6.md`](releases/0.1.0b6.md).

Current source candidate state:

- [x] The unpublished `0.1.0b7` release candidate is the package-metadata and
      main-branch documentation target. Review the
      [candidate notes](releases/0.1.0b7.md) and
      [evaluation guide](upgrading-to-0.1.0b7.md).
- [ ] `0.1.0b7` becomes the current external release only after the exact
      candidate commit passes the complete release matrix, TestPyPI and PyPI
      smokes pass, and publication evidence replaces candidate intent in the
      [release index](releases/README.md).

Current pre-case-study decision:

- [x] Pre-case-study hardening complete; measured proof work promoted to
      Phase 89.

## Completed: Critical Stabilization

The release-blocking findings from the 2026-07-09 deep audit were implemented,
verified, and merged through protected PR #345. The decision-complete
implementation and release-readiness contract is:

[`docs/roadmap/critical-stabilization.md`](roadmap/critical-stabilization.md).

The program used focused commits on its dedicated integration branch and passed
the required local and hosted verification. External `0.1.0b6` publication is
recorded in the release evidence above.

## Completed Phase Archive

Completed roadmap history is bucketed so this active tracker stays short and
cheap for agents to scan. Use these files when historical recovery context is
needed:

- [Roadmap archive map](roadmap/archive/README.md)
- [Foundations and release hardening, phases 001-073](roadmap/archive/completed-phases-001-073-foundations-release-hardening.md)
- [Provider and policy stabilization, phases 074-108](roadmap/archive/completed-phases-074-108-provider-policy-stabilization.md)
- [Internal package extraction, phases 109-123](roadmap/archive/completed-phases-109-123-internal-package-extraction.md)
- [DocSync, provider evidence, and runtime, phases 124-144](roadmap/archive/completed-phases-124-144-docsync-provider-runtime.md)
- [Runtime context ROI, phases 145-148](roadmap/archive/completed-phases-145-148-runtime-context-roi.md)

## Completed: Future-Call ROI Acceleration Track

Agent Maintainer should convert local primitives into compounding leverage for future agent calls. This track prioritizes work by expected return on cost, quality, and speed: runtime-event intelligence, repair-fact coverage, surgical next actions, DocSync verifier integration, attention scoring, and a hermetic downstream task-broker incubator.
Detailed scope: [`docs/roadmap/future-call-roi-acceleration.md`](roadmap/future-call-roi-acceleration.md)

Track work:

- [x] Phase 149: DocSync Verifier Integration Repair Facts
- [x] Phases 150-164: remaining ROI acceleration work in the detailed scope

## Completed: TypeScript/React Provider Maturation

Return to polyglot work through the existing TypeScript/JavaScript provider
track. Focus first on TypeScript and React repositories, not new ecosystems.
Keep the provider experimental until evidence satisfies the promotion bar in
[`docs/case-studies/typescript-provider-maturation.md`](case-studies/typescript-provider-maturation.md).

Track work:

- [x] Phases 165-175: TypeScript/React maturation work in the detailed scope

## Completed: Codex Wait And Rewake Hardening

This is separate from TypeScript/React provider maturation. The goal is to make
known waits act like real suspension primitives: local watchers own pending
polling, and Codex receives exactly one terminal continuation when a supported
local rewake backend is available.

Detailed scope:
[`docs/roadmap/phases/phase-176-codex-terminal-rewake-hardening.md`](roadmap/phases/phase-176-codex-terminal-rewake-hardening.md).

Track work:

- [x] Phase 176: Codex Terminal Rewake Hardening — the read-only and explicitly
      gated real-turn smokes passed; terminal rewake remains opt-in.

## Active: External Proof And Architecture Hardening

The next product milestone is external activation evidence, not another broad
feature phase. Run a three-to-five-repository cohort covering at least 30 real
coding-agent tasks, and measure activation time, initializer conflicts,
false-positive review findings, repair iterations, context expansions, review
cost, and four-week retained use.

Strict Pyright cutover complete: zero diagnostics and the former ratchet
baseline are retired.

- [ ] External proof: run the three-to-five-repository cohort and retain its
      activation and use evidence.
- [x] Strict Pyright cutover complete: zero diagnostics; baseline retired.
- [x] Reclassify top-level help and public docs into stable workflow, repair and
      inspection, optional local intelligence, experimental integrations, and
      operations. Keep basic quiet waits distinct from experimental rewake.
- [x] Guarantee changed, failed, exact-fact, and explicitly requested paths are
      retained when attention-ledger sampling caps large repositories.
- [x] Validate attention schema version, file count, normalized paths, and
      finite `0..1` scores; label context relevance as direct, inferred, or
      background and omit background notes from tight hook output.
- [x] Add `agent_waits` to the internal-package current-state document and
      secondary dependency-direction regression coverage.
- [x] Publish exact-installed-version expectations and unfrozen current entry
      points for commands, formats, and internal top-level packages.

## Future Work

- Keep agent orchestration framework work behind replaceable adapter contracts:
  [`docs/roadmap/agent-orchestration-adapter-doctrine.md`](roadmap/agent-orchestration-adapter-doctrine.md).

- Continue adding section-level DocSync claims as public docs materially change,
  especially where a claim can point to durable implementation or test evidence.

- Avoid adding new ecosystems until TypeScript/JavaScript satisfies the
  promotion bar in

  [`docs/case-studies/typescript-provider-maturation.md`](case-studies/typescript-provider-maturation.md).

## Final Definition Of Done

The roadmap is complete only when every phase above is implemented, tested,
documented, merged through CI, and verified against the final definition of
done in [`docs/roadmap/final-definition-of-done.md`](roadmap/final-definition-of-done.md).
