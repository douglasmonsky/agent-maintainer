# Roadmap

## Read This First

This file is only the implementation tracker for the Agent Maintainer roadmap.
It is a recovery checklist, not the detailed implementation spec.

The canonical detailed spec is vendored into the repository here:

[`docs/roadmap/full-roadmap-blueprint.md`](roadmap/full-roadmap-blueprint.md).

The usage guide for that spec is here:

[`docs/roadmap/README.md`](roadmap/README.md).

Before implementing any phase:

1. Open [`docs/roadmap/README.md`](roadmap/README.md).
2. Reopen the matching phase in
   [`docs/roadmap/full-roadmap-blueprint.md`](roadmap/full-roadmap-blueprint.md).
3. Follow that phase's scope, file targets, tests, documentation requirements,
   acceptance criteria, and explicit out-of-scope rules.
4. Use this file only to track phase completion after implementation,
   verification, merge, and post-merge CI confirmation.

Do not infer phase requirements from this checklist alone. If chat context is
compacted or interrupted, resume from this checklist only after reopening the
guide and full blueprint. If the detailed blueprint appears missing or stale,
restore the source document named `agent-maintainer-full-roadmap-blueprint.md`
before continuing implementation.

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

- [ ] Postpone Future Work until pre-case-study hardening is complete.

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
- [ ] Phase 64: Documentation and Generated Guidance Slimming

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

## Future Work

These items are intentionally postponed and are not part of the current
roadmap completion gate.

- External Case Studies and Measured Proof Harness
- Monorepo / Multi-Package Support
- Optional Compression Backends
- Team Policy Templates
- Headroom Integration

## Final Definition Of Done

The roadmap is complete only when every phase above is implemented, tested,
documented, merged through CI, and verified against the final definition of
done in the full blueprint.
