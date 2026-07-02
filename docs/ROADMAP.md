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

- [x] `agent-maintainer==0.1.0b4` is published to TestPyPI and PyPI,
      attached to GitHub prerelease `v0.1.0b4`, and smoke-tested from both
      package indexes. Release evidence is recorded in
      [`docs/releases/0.1.0b4.md`](releases/0.1.0b4.md).

Current pre-case-study decision:

- [x] Pre-case-study hardening complete; measured proof work promoted to
      Phase 89.

## Next: Context-Safe Legacy Ratchets

Agent Maintainer's next focus is helping agents improve existing repositories
without drowning in failures, giant files, huge diffs.

Planned work:

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

## Next: Quiet Control Plane And Dogfood Drift

Before external case studies resume, Agent Maintainer should reduce agent
context noise while preserving strict verification. Planned work:

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

## Next: Overnight Hardening

Before external case studies resume, Agent Maintainer should stay strict
without flooding agent context. This hardening pass is the active recovery
checklist and must be implemented in small PRs.

Planned work:

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

## Next: Advisory Sweep Survivor Triage

- [x] Phase 65: Mutation Sweep Executor Survivor Triage
- [x] Phase 66: Advisory Sweep Survivor Triage

Current advisory sweep findings remain non-blocking backlog:

- `src/agent_maintainer/core/reporting.py`: reduced from 124 to 39 survivors,
  not promotion-ready.
- `src/agent_maintainer/doctor/cli.py`: reduced from 270 to 11 survivors, not
  promotion-ready.

Planned work:

- Reduce `core/reporting.py` survivors first and document before/after counts.
- Refactor `doctor/cli.py` before survivor-chasing if survivor clusters show CLI
  plumbing rather than behavior contracts.
- Keep current blocking Mutmut targets unchanged until advisory candidates are
  promotion-ready.

## Next: Public Docs, Setup Advisor, and Technical Debt Score

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

## Next: Release Polish, Debt Score Clarity, Mutation UX, and Cohesion

Continue release polish without adding new scanners or public profile
semantics. Detailed scope:

[`docs/roadmap/phases/phase-73-release-polish-debt-mutation-and-cohesion.md`](roadmap/phases/phase-73-release-polish-debt-mutation-and-cohesion.md)

Planned work:

- [x] Phase 73: Release Polish, Debt Score Clarity, Mutation UX, and Cohesion

## Next: Review-Driven Stabilization

Static review identified the next release-risk area as drift across Agent
Maintainer's broad public surface: config fields, env vars, CLI overrides,
starter files, optional gates, generated artifacts, and docs. Stabilization
should take priority over new scanner categories.

Detailed scope:

[`docs/roadmap/phases/phase-74-review-driven-stabilization.md`](roadmap/phases/phase-74-review-driven-stabilization.md)

Planned work:

- [x] Phase 74: Review-Driven Stabilization Metadata, Schedules, and Output Contracts

## Next: Below-10 Debt And Strict Typing Ratchets

Agent Maintainer should be a beacon-level dogfood repo before external case
studies resume. This phase lowers the advisory Technical Debt Score below 10,
adds strict Pyright ratcheting without flipping the whole repo to strict mode,
reduces real mutation survivors, and keeps cleanup refactors evidence-backed.

Detailed scope:

[`docs/roadmap/phases/phase-75-below-10-debt-and-strict-typing-ratchets.md`](roadmap/phases/phase-75-below-10-debt-and-strict-typing-ratchets.md)

Planned work:

- [x] Phase 75: Below-10 Debt, Strict Pyright Ratchets, and Beacon-Level Dogfooding

## Next: Ecosystem Provider Roadmap

Agent Maintainer should plan the provider architecture before moving Python
catalog and policy behavior. This phase creates the polyglot provider roadmap
without runtime behavior changes, provider implementation, new language support,
or config migration. Detailed scope:

[`docs/roadmap/phases/phase-76-ecosystem-provider-roadmap.md`](roadmap/phases/phase-76-ecosystem-provider-roadmap.md)

Planned work:

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
- [x] Phase 87: Experimental Go Provider
- [x] Phase 88: Provider API Stability Decision
- [x] Phase 89: Measured Repair Case Studies
- [x] Phase 90: Workspace Config Foundation
- [x] Phase 91: Team Policy Templates
- [x] Phase 92: Roadmap Future Work Cleanup

## Next: Provider Stabilization And Doctor Alignment

The provider refactor has landed, but Agent Maintainer should harden the seam
before adding more languages or claiming mature polyglot support. This phase
keeps Python the core/reference provider, keeps TypeScript and Go experimental,
and aligns provider metadata, doctor output, and tool capability hints.
Detailed scope:

[`docs/roadmap/phases/phase-93-provider-stabilization-and-doctor-alignment.md`](roadmap/phases/phase-93-provider-stabilization-and-doctor-alignment.md)

Planned work:

- [x] Phase 93: Provider Stabilization And Doctor Alignment

## Next: Multi-Ecosystem Reviewability Policy Design

Agent Maintainer should not overclaim polyglot reviewability yet. Current
reviewability checks are globally scheduled but Python-backed. This phase
records the policy direction for change budgets, suppressions, file length,
structure cohesion, and future file-change classification before those checks
are generalized across TypeScript, Go, or later providers.
Detailed scope:

[`docs/roadmap/phases/phase-94-multi-ecosystem-reviewability-policy-design.md`](roadmap/phases/phase-94-multi-ecosystem-reviewability-policy-design.md)

Planned work:

- [x] Phase 94: Multi-Ecosystem Reviewability Policy Design

## Next: Provider-Aware File Change Classification

Agent Maintainer should now implement the internal file-change
classification seam designed in Phase 94. This phase keeps Python
reviewability behavior unchanged while making changed-file role and ecosystem
facts explicit for future advisory TypeScript/JavaScript and Go policy work.
Detailed scope:

[`docs/roadmap/phases/phase-95-provider-aware-file-change-classification.md`](roadmap/phases/phase-95-provider-aware-file-change-classification.md)

Planned work:

- [x] Phase 95: Provider-Aware File Change Classification

## Next: Advisory Reviewability Assessment

Agent Maintainer should surface provider-aware changed-file facts without
turning experimental TypeScript/JavaScript or Go support into blocking policy.
This phase adds a low-noise advisory assessment that reports changed files by
ecosystem and role, then points users to current Python-only blocking policy.
Detailed scope:

[`docs/roadmap/phases/phase-96-advisory-reviewability-assessment.md`](roadmap/phases/phase-96-advisory-reviewability-assessment.md)

Planned work:

- [x] Phase 96: Advisory Reviewability Assessment

## Next: Advisory Ecosystem Suppression Classification

Agent Maintainer should make ecosystem-specific suppression additions visible
without widening the current blocking Python suppression budget. This phase adds
provider-owned advisory suppression classifiers for TypeScript/JavaScript and Go
and surfaces counts through `assess reviewability`.
Detailed scope:

[`docs/roadmap/phases/phase-97-advisory-ecosystem-suppression-classification.md`](roadmap/phases/phase-97-advisory-ecosystem-suppression-classification.md)

Planned work:

- [ ] Phase 97: Advisory Ecosystem Suppression Classification

## Future Work

No active Future Work items remain in the current roadmap completion gate.
Former future-work items were either promoted to numbered phases or already
covered by completed compression/Headroom phases.

## Final Definition Of Done

The roadmap is complete only when every phase above is implemented, tested,
documented, merged through CI, and verified against the final definition of
done in [`docs/roadmap/final-definition-of-done.md`](roadmap/final-definition-of-done.md).
