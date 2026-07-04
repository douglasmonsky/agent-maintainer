# Completed Phases 074-108

This archive bucket preserves completed roadmap history so `docs/ROADMAP.md` stays focused on active work.

## Completed: Review-Driven Stabilization

Static review identified the next release-risk area as drift across Agent
Maintainer's broad public surface: config fields, env vars, CLI overrides,
starter files, optional gates, generated artifacts, and docs. Stabilization
should take priority over new scanner categories.

Detailed scope:

[`docs/roadmap/phases/phase-74-review-driven-stabilization.md`](roadmap/phases/phase-74-review-driven-stabilization.md)

Completed work:

- [x] Phase 74: Review-Driven Stabilization Metadata, Schedules, and Output Contracts

## Completed: Below-10 Debt And Strict Typing Ratchets

Agent Maintainer should be a beacon-level dogfood repo before external case
studies resume. This phase lowers the advisory Technical Debt Score below 10,
adds strict Pyright ratcheting without flipping the whole repo to strict mode,
reduces real mutation survivors, and keeps cleanup refactors evidence-backed.

Detailed scope:

[`docs/roadmap/phases/phase-75-below-10-debt-and-strict-typing-ratchets.md`](roadmap/phases/phase-75-below-10-debt-and-strict-typing-ratchets.md)

Completed work:

- [x] Phase 75: Below-10 Debt, Strict Pyright Ratchets, and Beacon-Level Dogfooding

## Completed: Ecosystem Provider Roadmap

Agent Maintainer should plan the provider architecture before moving Python
catalog and policy behavior. This phase creates the polyglot provider roadmap
without runtime behavior changes, provider implementation, new language support,
or config migration. Detailed scope:

[`docs/roadmap/phases/phase-76-ecosystem-provider-roadmap.md`](roadmap/phases/phase-76-ecosystem-provider-roadmap.md)

Completed work:

- [x] Phase 76: Ecosystem Provider Roadmap
- [x] Phase 77: Ecosystem Provider Characterization Safety Net
- [x] Phase 78: Minimal Internal Python Provider Seam
- [x] Phase 79: Global And Ecosystem Check Ownership
- [x] Phase 80: Generic File Classification, Python Only
- [x] Phase 81: Policy Checks Through Python Classifier Adapters
- [x] Phase 82: Neutral Config Path Exploration
- [x] Phase 83: Experimental TypeScript/JavaScript Provider
- [x] Phase 84: TypeScript Provider Doctor Hints And Fixture Smoke Tests
- [x] Phase 85: TypeScript Structured Output Repair Facts
- [x] Phase 86: Provider Contribution Guide
- [x] Phase 88: Provider API Stability Decision
- [x] Phase 89: Measured Repair Case Studies
- [x] Phase 90: Workspace Config Foundation
- [x] Phase 91: Team Policy Templates
- [x] Phase 92: Roadmap Future Work Cleanup

## Completed: Provider Stabilization And Doctor Alignment

The provider refactor has landed, but Agent Maintainer should harden the seam
before adding more languages or claiming mature polyglot support. This phase
keeps Python the core/reference provider and TypeScript/JavaScript experimental,
and aligns provider metadata, doctor output, and tool capability hints.
Detailed scope:

[`docs/roadmap/phases/phase-93-provider-stabilization-and-doctor-alignment.md`](roadmap/phases/phase-93-provider-stabilization-and-doctor-alignment.md)

Completed work:

- [x] Phase 93: Provider Stabilization And Doctor Alignment

## Completed: Multi-Ecosystem Reviewability Policy Design

Agent Maintainer should not overclaim polyglot reviewability yet. Current
reviewability checks are globally scheduled but Python-backed. This phase
records the policy direction for change budgets, suppressions, file length,
structure cohesion, and future file-change classification before those checks
are generalized across TypeScript/JavaScript or later providers.
Detailed scope:

[`docs/roadmap/phases/phase-94-multi-ecosystem-reviewability-policy-design.md`](roadmap/phases/phase-94-multi-ecosystem-reviewability-policy-design.md)

Completed work:

- [x] Phase 94: Multi-Ecosystem Reviewability Policy Design

## Completed: Provider-Aware File Change Classification

Agent Maintainer should now implement the internal file-change
classification seam designed in Phase 94. This phase keeps Python
reviewability behavior unchanged while making changed-file role and ecosystem
facts explicit for future advisory TypeScript/JavaScript policy work.
Detailed scope:

[`docs/roadmap/phases/phase-95-provider-aware-file-change-classification.md`](roadmap/phases/phase-95-provider-aware-file-change-classification.md)

Completed work:

- [x] Phase 95: Provider-Aware File Change Classification

## Completed: Advisory Reviewability Assessment

Agent Maintainer should surface provider-aware changed-file facts without
turning experimental TypeScript/JavaScript support into blocking policy.
This phase adds a low-noise advisory assessment that reports changed files by
ecosystem and role, then points users to current Python-only blocking policy.
Detailed scope:

[`docs/roadmap/phases/phase-96-advisory-reviewability-assessment.md`](roadmap/phases/phase-96-advisory-reviewability-assessment.md)

Completed work:

- [x] Phase 96: Advisory Reviewability Assessment

## Completed: Advisory Ecosystem Suppression Classification

Agent Maintainer should make ecosystem-specific suppression additions visible
without widening the current blocking Python suppression budget. This phase adds
provider-owned advisory suppression classifiers for TypeScript/JavaScript
and surfaces counts through `assess reviewability`.
Detailed scope:

[`docs/roadmap/phases/phase-97-advisory-ecosystem-suppression-classification.md`](roadmap/phases/phase-97-advisory-ecosystem-suppression-classification.md)

Completed work:

- [x] Phase 97: Advisory Ecosystem Suppression Classification

## Completed: TypeScript Reviewability Fixture Evidence

Agent Maintainer should validate TypeScript/JavaScript reviewability
signal before adding more ecosystems or blocking policy. This phase adds
fixture-style evidence for changed-file roles, dependency changes, generated
files, and advisory suppressions while splitting advisory change collection from
the Python change-budget filter.
Detailed scope:

[`docs/roadmap/phases/phase-98-typescript-reviewability-fixture-evidence.md`](roadmap/phases/phase-98-typescript-reviewability-fixture-evidence.md)

Completed work:

- [x] Phase 98: TypeScript Reviewability Fixture Evidence

## Completed: Advisory Provider Reviewability Summaries

Agent Maintainer should turn fixture evidence into more useful advisory output
before adding blocking policy. This phase adds provider source/test summaries,
TypeScript/JavaScript source/test advisory findings, and broad suppression
findings while keeping TypeScript/JavaScript non-blocking.
Detailed scope:

[`docs/roadmap/phases/phase-99-advisory-provider-reviewability-summaries.md`](roadmap/phases/phase-99-advisory-provider-reviewability-summaries.md)

Completed work:

- [x] Phase 99: Advisory Provider Reviewability Summaries

## Completed: TypeScript Provider Maturation

Agent Maintainer should mature TypeScript/JavaScript as the first serious
non-Python provider while focusing on TypeScript/JavaScript maturation. This
phase validates TypeScript provider depth with fixture evidence and provider
notes without adding new ecosystems or blocking TypeScript gates.

Detailed scope:

[`docs/roadmap/phases/phase-100-typescript-provider-maturation.md`](roadmap/phases/phase-100-typescript-provider-maturation.md)

Completed work:

- [x] Phase 100: TypeScript Provider Maturation

## Completed: TypeScript Advisory Threshold Evidence

Agent Maintainer should use the TypeScript fixture evidence to decide which
advisory signals are stable enough for future configurable thresholds while
keeping TypeScript non-blocking.

Detailed scope:

[`docs/roadmap/phases/phase-101-typescript-advisory-threshold-evidence.md`](roadmap/phases/phase-101-typescript-advisory-threshold-evidence.md)

Completed work:

- [x] Phase 101: TypeScript Advisory Threshold Evidence

## Completed: TypeScript Setup Advisor Recommendations

Agent Maintainer should help adopters configure the experimental TypeScript
provider when package scripts already expose lint, typecheck, or test
commands, without guessing package managers or adding blocking TypeScript
policy.

Detailed scope:

[`docs/roadmap/phases/phase-102-typescript-setup-advisor.md`](roadmap/phases/phase-102-typescript-setup-advisor.md)

Completed work:

- [x] Phase 102: TypeScript Setup Advisor Recommendations

## Completed: TypeScript Test Repair Facts

Agent Maintainer should extract concise repair facts from explicitly configured
TypeScript/JavaScript test output when the output uses a supported JSON shape.
This is structured repair support for the experimental TypeScript provider, not
package-manager autodetection or blocking TypeScript policy.

Detailed scope:

[`docs/roadmap/phases/phase-104-typescript-test-repair-facts.md`](roadmap/phases/phase-104-typescript-test-repair-facts.md)

Completed work:

- [x] Phase 104: TypeScript Test Repair Facts

## Latest Completed: Provider Dispatch Registry

Agent Maintainer should keep provider-specific classification and advisory
suppression dispatch behind the internal registry instead of direct imports in
assessment helpers. This is provider-seam stabilization, not new language
support or public plugin API work.

Detailed scope:

[`docs/roadmap/phases/phase-105-provider-dispatch-registry.md`](roadmap/phases/phase-105-provider-dispatch-registry.md)

Completed work:

- [x] Phase 105: Provider Dispatch Registry

## Latest Completed: Archive Go Provider History Out Of Main

Agent Maintainer should remove the Go-provider experiment from active `main`
now that the experiment is preserved on `archive/go-provider-experiment` and
TypeScript/JavaScript is the only active non-Python maturation track.

Detailed scope:

[`docs/roadmap/phases/phase-106-archive-go-provider-history.md`](roadmap/phases/phase-106-archive-go-provider-history.md)

Completed work:

- [x] Phase 106: Archive Go Provider History Out Of Main

## Completed: Roadmap Status Label Cleanup

The roadmap tracker should not label already-completed sections as `Next`.
Normalize completed-section labels so future agents can recover the actual
current state without mistaking old phase summaries for active work.

Detailed scope:

[`docs/roadmap/phases/phase-107-roadmap-status-label-cleanup.md`](roadmap/phases/phase-107-roadmap-status-label-cleanup.md)

Completed work:

- [x] Phase 107: Roadmap Status Label Cleanup

## Completed: Repair Capsule Output Contract And Pointer-First Context

Agent Maintainer should give agents a strict, compact repair capsule instead of
nudging them to load full verifier transcripts or full context packs. Context
pack generation remains available, but agent-facing hook and verifier output
should point to run-scoped artifacts and one expansion command by default.

Detailed scope:

[`docs/roadmap/phases/phase-108-repair-capsule-output-contract.md`](roadmap/phases/phase-108-repair-capsule-output-contract.md)

Completed work:

- [x] Phase 108: Repair Capsule Output Contract And Pointer-First Context
