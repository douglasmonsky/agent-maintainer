# Roadmap

## Read This First

This file is only the implementation tracker for the Agent Maintainer roadmap.
It is a recovery checklist, not the detailed implementation spec.

The canonical detailed spec index is vendored into the repository here:

[`docs/roadmap/full-roadmap-blueprint.md`](roadmap/full-roadmap-blueprint.md).

The usage guide for the split specs is here:

[`docs/roadmap/README.md`](roadmap/README.md).

Experimental architecture track:

[`docs/roadmap/polyglot-ecosystem-providers.md`](roadmap/polyglot-ecosystem-providers.md).

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

Agent Maintainer is in beta. The current major roadmap covers context-safe
legacy ratchets, test intelligence, planned large-change support, and optional
compression. Do not collapse it into one large PR. The blueprint requires one
phase per PR unless the user explicitly changes that rule.

## Current Baseline

The public beta baseline already includes package-first onboarding, verification
profiles, diagnostics, release checks, public packaging metadata, TestPyPI/PyPI
Trusted Publishing workflow, Codex and Claude Code hooks, generated guidance,
example repos, and the first cohesive-change budget exception.

Current external release state:

- [x] `agent-maintainer==0.1.0b5` is published to TestPyPI and PyPI,
      attached to GitHub prerelease `v0.1.0b5`, and smoke-tested from both
      package indexes. Release evidence is recorded in
      [`docs/releases/0.1.0b5.md`](releases/0.1.0b5.md).

Current pre-case-study decision:

- [x] Pre-case-study hardening complete; measured proof work promoted to
      Phase 89.

## Completed: DocSync Foundation

DocSync now exists as an extractable sibling package under `src/docsync/`.
It connects stable Markdown documentation objects to explicit source, test,
schema, configuration, and generated-artifact evidence regions through the
human-authored `.docsync/trace.yml` graph.

Completed foundation capabilities:

- `src/docsync/` is a sibling package, not a child of `agent_maintainer/`.
- `.docsync/config.yml`, `.docsync/trace.yml`, `.docsync/schema.json`,
  `.docsync/attestations/`, and `.docsync/out/` exist with generated output
  kept out of source truth.
- `AGENTS.md` records DocSync package-boundary rules.
- Evidence regions use `docsync:evidence.start` and `docsync:evidence.end`.
- Markdown objects use hidden `<!-- docsync:object ... -->` identifiers.
- DocSync validates the trace graph, indexes evidence, maps changed evidence
  to documentation claims, supports attestations, and generates review packets.
- CLI commands include `docsync index`, `docsync check`, `docsync prompt`,
  `docsync attest`, and `docsync doctor`.
- Boundary tests keep DocSync extractable and independent from
  `agent_maintainer` and `archguard`.

Current evidence lives in `docs/docsync-extraction.md`, `.docsync/trace.yml`,
`tests/docsync/`, and the DocSync dogfood phases 114, 117, and 120 through 122.
The knowledge graph, local vector index, GraphQL query layer, and repo wiki
projection prototype remain intentionally out of scope on
`experiment/docsync-knowledge-graph`.

## Completed: Context-Safe Legacy Ratchets

Agent Maintainer's next focus is helping agents improve existing repositories
without drowning in failures, giant files, huge diffs.

Completed work:

- Bounded failure summaries with explicit expansion commands.
- Test intelligence for changed source and relevant tests.
- Safe context commands for logs, failures, files, and diffs.
- Python file outlines for large legacy files.
- Context packs for agent repair loops.
- Ratchet baselines with ranked repair targets.
- Generated `AGENTS.ratchet.md` guidance.
- Cohesive change plans for intentional large migrations.
- Integration branch series support for large rewrites.
- Optional compression backends for sanitized supporting context.
- PR summaries with measured proof examples.

## Implementation Phases

- [x] Phase 1: ADR Context-Safe Legacy Ratchets
- [x] Phase 2: ADR Test Intelligence Ladder
- [x] Phase 3: Public Roadmap Docs Stubs
- [x] Phase 4: Config Scaffolding
- [x] Phase 5: Context Contract Implementation
- [x] Phase 6: Bounded Verifier, Hook, LAST_FAILURE Output
- [x] Phase 7: Test Intelligence MVP
- [x] Phase 8: Smarter Source-Without-Test Guidance
- [x] Phase 9: `context failures` and `context log`
- [x] Phase 10: Context Budget Estimation
- [x] Phase 11: Safe Large-File Reading
- [x] Phase 12: Diff Context Safety
- [x] Phase 13: Ratchet Baseline Status
- [x] Phase 14: Ratchet Target Ranking
- [x] Phase 15: Generate `AGENTS.ratchet.md`
- [x] Phase 16: Context Packs
- [x] Phase 17: Hook Output Uses Context Packs
- [x] Phase 18: Context Artifact Retention Upload Policy
- [x] Phase 19: Hypothesis Candidate Guidance
- [x] Phase 20: Mutmut Target Suggestions
- [x] Phase 21: CrossHair Candidate Guidance
- [x] Phase 22: Cohesive Change Plans
- [x] Phase 23: Change-Budget Integration Change Plans
- [x] Phase 24: Integration Branch Series
- [x] Phase 25: Compression Backend Interface
- [x] Phase 26: Optional Headroom Backend
- [x] Phase 27: Doctor Integration
- [x] Phase 28: Examples Proof Repos
- [x] Phase 29: PR / GitHub Actions Summary Report
- [x] Phase 30: Policy Packs Onboarding Presets
- [x] Phase 31: Archguard Impact Analysis
- [x] Phase 32: Repair Plan Command
- [x] Phase 33: Agent Adapter API
- [x] Phase 34: Tach Architecture Contract Refit
- [x] Phase 35: Static HTML Report
- [x] Phase 36: Review-Driven Stabilization Plan
- [x] Phase 37: Headroom Backend Correctness
- [x] Phase 38: Change-Plan Authority Over Legacy Overrides
- [x] Phase 39: Coverage Semantics Hardening
- [x] Phase 40: Exact Repair Facts From Structured Artifacts
- [x] Phase 41: Beta Release Metadata Refresh
- [x] Phase 42: Pre-Case-Study Hardening Plan
- [x] Phase 43: Context Package Boundary Split
      Completed in PR #116. The remaining work after that PR is ordinary
      domain-specific hardening, not another boundary-split phase.
- [x] Phase 44: Hook Output Invariant Tests
- [x] Phase 45: Release-Check Ergonomics
- [x] Phase 46: Release-State Drift Check

## Completed: Quiet Control Plane And Dogfood Drift

Before external case studies resume, Agent Maintainer should reduce agent
context noise while preserving strict verification. Completed work:

- Commit current context-boundary and verifier-artifact refactor as an early
  milestone after cleanup.
- Keep agent-facing verifier output summary-first: pass/fail, profile, run id,
  failed checks, exact next commands.
- Keep raw logs and long diagnostics in run-scoped `.verify-logs/runs/<run-id>/`
  artifacts instead of chat output.
- Document agent narration discipline: no routine waiting chatter, no narrating
  every focused rerun, batch check results, and use `apply_patch` for manual
  edits.
- Encode verification cadence: focused checks during the edit loop, `precommit`
  before commit, full profile set once before PR/merge, release checks only for
  release work.
- Add dogfood drift detection so this repository verifies against local
  `src/agent_maintainer` code, not stale installed package code.
- Preserve configured-repo-only hooks: global hook install may exist, but hooks
  no-op outside repos with `[tool.agent_maintainer]`.

## Quiet Control Plane Phases

- [x] Phase 47: Commit Context Boundary And Run Artifact Refactor
- [x] Phase 48: Quiet Agent Output And Guidance Discipline
- [x] Phase 49: Verification Cadence Recommendations
- [x] Phase 50: Dogfood Drift Doctor Check
- [x] Phase 51: Duplicate Artifact Detection And Cleanup Guard
- [x] Phase 52: Configured-Repo Hook No-Op Tests

## Completed: Overnight Hardening

Before external case studies resume, Agent Maintainer should stay strict
without flooding agent context. This hardening pass is the active recovery
checklist and must be implemented in small PRs.

Completed work:

- Ship the current Mutmut target-ratchet branch as the first behavior
  milestone.
- Mature mutation testing beyond target count: better Mutmut config, result
  ratchets, and an advisory deep sweep.
- Keep verifier output summary-first: pass/fail, profile, run id, duration,
  failed checks, exact next commands.
- Keep raw logs and long diagnostics in run-scoped
  `.verify-logs/runs/<run-id>/` artifacts instead of chat or hook transcripts.
- Encode verification cadence: focused checks during edit loop, `precommit`
  before commit, full profile set once before PR/merge, release checks only for
  release work.
- Add dogfood drift detection so this checkout verifies local
  `src/agent_maintainer` code, not stale installed package code.
- Preserve configured-repo-only hooks: global hook install may exist, but hooks
  no-op outside repos with `[tool.agent_maintainer]`.
- Slim generated agent guidance and move detailed gate explanation into
  human-readable docs.

## Overnight Hardening Phases

- [x] Phase 53: Roadmap-First Overnight Hardening Plan
- [x] Phase 54: Ship Mutmut Target Ratchet Branch
- [x] Phase 55: Mutmut Config Hardening
- [x] Phase 56: Mutation Result Ratchets
- [x] Phase 57: Advisory Deep Mutation Sweep
- [x] Phase 58: Quiet Verifier Output Contract
- [x] Phase 59: Smarter Verification Cadence Guidance
- [x] Phase 60: Dogfood Source-Checkout Drift Detection
- [x] Phase 61: Run-Scoped Diagnostic Retention
- [x] Phase 62: Duplicate Generated Artifact Detection
- [x] Phase 63: Configured-Repo-Only Codex and Claude Hooks
- [x] Phase 64: Documentation and Generated Guidance Slimming

Acceptance criteria for this sequence:

- Targeted Mutmut remains the blocking mutation gate; broad sweeps are advisory
  until runtime and signal quality are proven.
- Downstream defaults remain conservative; this repository dogfoods every
  relevant enabled feature.
- Verifier and hook output stays compact, with detailed evidence linked by run
  id.
- Existing CLI and profiles remain valid. No new scanners, old-name
  compatibility, or Headroom integration are included in this pass.
- Each behavior phase has focused tests, relevant docs, local verification, PR
  CI, merge, and post-merge `main` CI confirmation.

## Completed: Advisory Sweep Survivor Triage

- [x] Phase 65: Mutation Sweep Executor Survivor Triage
- [x] Phase 66: Advisory Sweep Survivor Triage

Current advisory sweep findings remain non-blocking backlog:

- `src/agent_maintainer/core/reporting.py`: reduced from 124 to 39 survivors,
  not promotion-ready.
- `src/agent_maintainer/doctor/cli.py`: reduced from 270 to 11 survivors, not
  promotion-ready.

Completed work:

- Reduce `core/reporting.py` survivors first and document before/after counts.
- Refactor `doctor/cli.py` before survivor-chasing if survivor clusters show CLI
  plumbing rather than behavior contracts.
- Keep current blocking Mutmut targets unchanged until advisory candidates are
  promotion-ready.

## Completed: Public Docs, Setup Advisor, and Technical Debt Score

Agent Maintainer public onboarding now presents the product as a package-first
maintenance layer for AI-assisted Python repositories. README links deeper docs
at the point of need, and the implemented `assess` commands help users and
agents choose setup and prioritize hardening work.

Detailed scope:

[`docs/roadmap/phases/phase-67-public-docs-onboarding-and-debt-score.md`](roadmap/phases/phase-67-public-docs-onboarding-and-debt-score.md)

Completed work:

- README emphasizes package-first onboarding, fresh strict trial, supported
  scans, ratchets, setup advisor, debt score, and just-in-time links.
- `docs/supported-scans-and-agent-use.md` documents scan/profile/agent usage.
- `python3 -m agent_maintainer assess setup` recommends track, preset, optional
  gates, and follow-up AI prompts from local repo evidence.
- `python3 -m agent_maintainer assess debt` writes transparent advisory score
  artifacts and the HTML report renders the score when present.
- The old HTML graphics render pipeline was removed; README keeps static PNG
  assets without adding image-generation tooling to the developer workflow.

## Public Docs And Score Phases

- [x] Phase 67: Public Docs, Setup Advisor, and Technical Debt Score
- [x] Phase 68: README Docs Information Architecture Rewrite
- [x] Phase 69: Supported Scan Matrix Agent Utilization Guide
- [x] Phase 70: Setup Advisor Command JSON Output
- [x] Phase 71: Technical Debt Score v0 Scorecard Report Integration
- [x] Phase 72: Static Product Graphics Strategy Cleanup

## Completed: Release Polish, Debt Score Clarity, Mutation UX, and Cohesion

Continue release polish without adding new scanners or public profile
semantics. Detailed scope:

[`docs/roadmap/phases/phase-73-release-polish-debt-mutation-and-cohesion.md`](roadmap/phases/phase-73-release-polish-debt-mutation-and-cohesion.md)

Completed work:

- [x] Phase 73: Release Polish, Debt Score Clarity, Mutation UX, and Cohesion

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

## Completed: Internal Package Boundary Refactor Roadmap

Agent Maintainer should split reusable primitives into internal packages only
after baseline characterization and package-boundary instructions are durable.
This phase adds the separate roadmap and preserves the exact implementation
handoff without moving runtime code.

Detailed scope:

[`docs/roadmap/phases/phase-109-internal-package-boundary-roadmap.md`](roadmap/phases/phase-109-internal-package-boundary-roadmap.md)

Detailed roadmap:

[`docs/roadmap/internal-package-boundaries.md`](roadmap/internal-package-boundaries.md)

Exact instructions:

[`docs/roadmap/internal-package-boundaries-implementation-guide.txt`](roadmap/internal-package-boundaries-implementation-guide.txt)

Completed work:

- [x] Phase 109: Internal Package Boundary Refactor Roadmap

## Completed: Internal Package Baseline And Ownership

Before moving runtime code into extracted internal packages, Agent Maintainer
captured current behavior and accepted the package ownership dependency
direction. DocSync now owns the docs/evidence boundary that earlier planning
called `docs_evidence`.

Detailed scope:

[`docs/roadmap/phases/phase-110-internal-package-baseline-and-ownership.md`](roadmap/phases/phase-110-internal-package-baseline-and-ownership.md)

Architecture decision:

[`docs/architecture/decisions/2026-07-02-internal-package-ownership.md`](architecture/decisions/2026-07-02-internal-package-ownership.md)

Completed work:

- [x] Phase 110: Internal Package Baseline And Ownership

## Completed: Agent Repair Facts Internal Package Extraction

Agent Maintainer should extract repair-fact payload normalization, parser
implementations, and parser dispatch into a new internal package,
`agent_repair_facts`, while preserving current context-pack behavior and old
import paths through compatibility shims.

Detailed scope:

[`docs/roadmap/phases/phase-111-agent-repair-facts-package.md`](roadmap/phases/phase-111-agent-repair-facts-package.md)

Internal package roadmap:

[`docs/roadmap/internal-package-boundaries.md`](roadmap/internal-package-boundaries.md)

Implementation guide:

[`docs/roadmap/internal-package-boundaries-implementation-guide.txt`](roadmap/internal-package-boundaries-implementation-guide.txt)

Completed work:

- [x] Phase 111: Agent Repair Facts Internal Package Extraction

## Completed: Agent Context Primitives And Reading Extraction

Agent Maintainer should begin the `agent_context` package extraction by moving
pure context primitives and reading utilities first, leaving product-coupled
context-pack CLI, ratchet, and verifier-artifact adapter work for follow-up.

Detailed scope:

[`docs/roadmap/phases/phase-112-agent-context-primitives.md`](roadmap/phases/phase-112-agent-context-primitives.md)

Internal package roadmap:

[`docs/roadmap/internal-package-boundaries.md`](roadmap/internal-package-boundaries.md)

Implementation guide:

[`docs/roadmap/internal-package-boundaries-implementation-guide.txt`](roadmap/internal-package-boundaries-implementation-guide.txt)

Completed work:

- [x] Phase 112: Agent Context Primitives And Reading Extraction

## Completed: Agent Run Artifacts Internal Package Extraction

Agent Maintainer should next extract verifier artifact schemas and rendering
helpers into `agent_run_artifacts`, preserving `.verify-logs` behavior, old
`agent_maintainer.verify.*` import paths, PR summary output, and run-scoped
diagnostic layout.

Detailed scope:

[`docs/roadmap/phases/phase-113-agent-run-artifacts-package.md`](roadmap/phases/phase-113-agent-run-artifacts-package.md)

Internal package roadmap:

[`docs/roadmap/internal-package-boundaries.md`](roadmap/internal-package-boundaries.md)

Implementation guide:

[`docs/roadmap/internal-package-boundaries-implementation-guide.txt`](roadmap/internal-package-boundaries-implementation-guide.txt)

Completed work:

- [x] Phase 113: Agent Run Artifacts Internal Package Extraction

## Completed: DocSync Dogfood Seed And Ratchet

DocSync should start dogfooding this repository on its own durable extraction
contract before broader docs coverage. This keeps the trace useful while the
package-extraction refactor is still moving.

Detailed scope:

[`docs/roadmap/phases/phase-114-docsync-dogfood-ratchet.md`](roadmap/phases/phase-114-docsync-dogfood-ratchet.md)

Completed work:

- [x] Phase 114: DocSync Dogfood Seed And Ratchet

## Completed: Agent Client Hooks Internal Package Extraction

Agent Maintainer should extract agent-client hook templates, merge helpers, and
install planning into `agent_client_hooks`, while keeping hook runtime
verification product-owned under `agent_maintainer.hooks`.

Detailed scope:

[`docs/roadmap/phases/phase-115-agent-client-hooks-package.md`](roadmap/phases/phase-115-agent-client-hooks-package.md)

Completed work:

- [x] Phase 115: Agent Client Hooks Internal Package Extraction

## Completed: Internal Package Boundary Regression Tests

Extracted internal packages should have executable dependency-direction checks
in addition to Tach domain contracts. This keeps future extraction work from
quietly importing product orchestration back into reusable packages.

Detailed scope:

[`docs/roadmap/phases/phase-116-internal-package-boundary-tests.md`](roadmap/phases/phase-116-internal-package-boundary-tests.md)

Completed work:

- [x] Phase 116: Internal Package Boundary Regression Tests

## Completed: README DocSync Evidence Ratchet

DocSync should now dogfood public documentation, not only its extraction note.
Start with README claims that users rely on during first adoption and repair
loops.

Detailed scope:

[`docs/roadmap/phases/phase-117-readme-docsync-evidence.md`](roadmap/phases/phase-117-readme-docsync-evidence.md)

Completed work:

- [x] Phase 117: README DocSync Evidence Ratchet

## Completed: Agent Context Pack Rendering Extraction

Continue internal package boundary refactor by moving pure context-pack
rendering and sanitizing helpers into `agent_context`, while keeping context
builder, compression, ratchet, and CLI orchestration product-owned.

Detailed scope:

[`docs/roadmap/phases/phase-118-agent-context-pack-rendering.md`](roadmap/phases/phase-118-agent-context-pack-rendering.md)

Completed work:

- [x] Phase 118: Agent Context Pack Rendering Extraction

## Completed: Agent Context Compression Extraction

Move reusable context compression primitives into `agent_context`, while keeping
context-pack compression orchestration, CLI/config behavior, and artifact
generation product-owned.

Detailed scope:

[`docs/roadmap/phases/phase-119-agent-context-compression.md`](roadmap/phases/phase-119-agent-context-compression.md)

Completed work:

- [x] Phase 119: Agent Context Compression Extraction

## Completed: Public Docs DocSync Ratchet

Expand DocSync from README-only dogfooding into the core public docs users
and agents follow during adoption, verification, diagnostics, ratcheting,
scan selection, and provider-status review.

Detailed scope:

[`docs/roadmap/phases/phase-120-docsync-public-docs-ratchet.md`](roadmap/phases/phase-120-docsync-public-docs-ratchet.md)

Completed work:

- [x] Phase 120: Public Docs DocSync Ratchet

## Completed: Operational DocSync Trace Closure

Close the stale roadmap gap after extending DocSync trace coverage into agent
hooks, context compression, release checklist, and architecture policy docs.

Detailed scope:

[`docs/roadmap/phases/phase-121-operational-docsync-trace-closure.md`](roadmap/phases/phase-121-operational-docsync-trace-closure.md)

Completed work:

- [x] Phase 121: Operational DocSync Trace Closure

## Completed: Provider-Specific DocSync Evidence

Extend DocSync dogfooding into provider-specific public docs for the active
TypeScript/JavaScript maturation track. This keeps provider docs tied to source
and test evidence while avoiding new ecosystem scope. Detailed scope:

[`docs/roadmap/phases/phase-122-provider-specific-docsync-evidence.md`](roadmap/phases/phase-122-provider-specific-docsync-evidence.md)

Completed work:

- [x] Phase 122: Provider-Specific DocSync Evidence

## Completed: Internal Package Refactor Docs Closure

Close stale recovery gap in internal-package refactor docs after extraction
phases landed. Future agents should see current package shape and remaining
invariants instead of instructions implying Phase 0 still needs to start.

Detailed scope:

[`docs/roadmap/phases/phase-123-internal-package-refactor-docs-closure.md`](roadmap/phases/phase-123-internal-package-refactor-docs-closure.md)

Completed work:

- [x] Phase 123: Internal Package Refactor Docs Closure

## Completed: DocSync Foundation Roadmap Closure

Close stale DocSync foundation roadmap text now implementation and dogfooding
have landed. The main roadmap should describe current capabilities and evidence
instead of an old planned execution list.

Detailed scope:

[`docs/roadmap/phases/phase-124-docsync-foundation-roadmap-closure.md`](roadmap/phases/phase-124-docsync-foundation-roadmap-closure.md)

Completed work:

- [x] Phase 124: DocSync Foundation Roadmap Closure

## Completed: Roadmap Blueprint Index Repair

Refresh compact roadmap blueprint index so it links every split phase spec and
add a test guard that fails when future phase files are omitted from the index.

Detailed scope:

[`docs/roadmap/phases/phase-125-roadmap-blueprint-index-repair.md`](roadmap/phases/phase-125-roadmap-blueprint-index-repair.md)

Completed work:

- [x] Phase 125: Roadmap Blueprint Index Repair

## Completed: Roadmap Overview Current State

Refresh the roadmap overview so it describes the current beta product state,
provider posture, internal packages, DocSync, repair capsule behavior, and
verification rules instead of the older context-safe-ratchet implementation
prompt.

Detailed scope:

[`docs/roadmap/phases/phase-126-roadmap-overview-current-state.md`](roadmap/phases/phase-126-roadmap-overview-current-state.md)

Completed work:

- [x] Phase 126: Roadmap Overview Current State

## Completed: Git Metadata Duplicate Artifact Warning

Extend duplicate-artifact doctor warnings to catch local Finder-style Git
metadata duplicates such as `.git/index 2`, while keeping cleanup manual and
warning-only.

Detailed scope:

[`docs/roadmap/phases/phase-127-git-metadata-duplicate-artifact-warning.md`](roadmap/phases/phase-127-git-metadata-duplicate-artifact-warning.md)

Completed work:

- [x] Phase 127: Git Metadata Duplicate Artifact Warning

## Completed: Active DocSync Coverage Ratchet

Make DocSync dogfood the active documentation set at the overview level by
requiring active docs to have trace document entries and live overview markers.

Detailed scope:

[`docs/roadmap/phases/phase-128-active-docsync-coverage-ratchet.md`](roadmap/phases/phase-128-active-docsync-coverage-ratchet.md)

Completed work:

- [x] Phase 128: Active DocSync Coverage Ratchet

## Completed: Mutation Results Artifact Fallback

Keep `test-intel mutation-results` useful after live `mutants/` artifacts are
cleaned by falling back to retained run and mutation-sweep diagnostics.

Detailed scope:

[`docs/roadmap/phases/phase-129-mutation-results-artifact-fallback.md`](roadmap/phases/phase-129-mutation-results-artifact-fallback.md)

Completed work:

- [x] Phase 129: Mutation Results Artifact Fallback

## Future Work

- Continue adding section-level DocSync claims as public docs materially change,
  especially where a claim can point to durable implementation or test evidence.
- Avoid adding new ecosystems until TypeScript/JavaScript satisfies the
  promotion bar in
  [`docs/case-studies/typescript-provider-maturation.md`](case-studies/typescript-provider-maturation.md).

## Final Definition Of Done

The roadmap is complete only when every phase above is implemented, tested,
documented, merged through CI, and verified against the final definition of
done in [`docs/roadmap/final-definition-of-done.md`](roadmap/final-definition-of-done.md).
