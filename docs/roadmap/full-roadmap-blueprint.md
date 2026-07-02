# Agent Maintainer Roadmap Blueprint

This file is the canonical roadmap index. Keep it small enough to read in
agent context. Detailed implementation specs live in split files under
`docs/roadmap/`.

Use `docs/ROADMAP.md` as the recovery checklist. Before implementing a
phase, open the matching detailed spec linked below. Do not re-expand this
index into a monolithic blueprint.

## Overview

- [Mission, baseline, architecture target, and execution rules](overview.md)

## Experimental Architecture Tracks

- [Polyglot Ecosystem Provider Roadmap](polyglot-ecosystem-providers.md)

## Phases

| Phase | Detailed Spec |
|---:|---|
| 76 | [Ecosystem Provider Roadmap](phases/phase-76-ecosystem-provider-roadmap.md) |
| 77 | [Ecosystem Provider Characterization Safety Net](phases/phase-77-ecosystem-provider-characterization-safety-net.md) |
| 78 | [Minimal Internal Python Provider Seam](phases/phase-78-minimal-internal-python-provider-seam.md) |
| 1 | [ADR for Context-Safe Legacy Ratchets](phases/phase-01-adr-for-context-safe-legacy-ratchets.md) |
| 2 | [ADR for Test Intelligence Ladder](phases/phase-02-adr-for-test-intelligence-ladder.md) |
| 3 | [Public Roadmap and Docs Stubs](phases/phase-03-public-roadmap-and-docs-stubs.md) |
| 4 | [Config Scaffolding](phases/phase-04-config-scaffolding.md) |
| 5 | [Context Contract Implementation](phases/phase-05-context-contract-implementation.md) |
| 6 | [Bounded Verifier, Hook, and LAST_FAILURE Output](phases/phase-06-bounded-verifier-hook-and-last-failure-output.md) |
| 7 | [Test Intelligence MVP](phases/phase-07-test-intelligence-mvp.md) |
| 8 | [Smarter Source-Without-Test Guidance](phases/phase-08-smarter-source-without-test-guidance.md) |
| 9 | [`context failures` and `context log`](phases/phase-09-context-failures-and-context-log.md) |
| 10 | [Context Budget Estimation](phases/phase-10-context-budget-estimation.md) |
| 11 | [Safe Large-File Reading](phases/phase-11-safe-large-file-reading.md) |
| 12 | [Diff Context Safety](phases/phase-12-diff-context-safety.md) |
| 13 | [Ratchet Baseline and Status](phases/phase-13-ratchet-baseline-and-status.md) |
| 14 | [Ratchet Target Ranking](phases/phase-14-ratchet-target-ranking.md) |
| 15 | [Generate `AGENTS.ratchet.md`](phases/phase-15-generate-agents-ratchet-md.md) |
| 16 | [Context Packs](phases/phase-16-context-packs.md) |
| 17 | [Hook Output Uses Context Packs](phases/phase-17-hook-output-uses-context-packs.md) |
| 18 | [Context Artifact Retention and Upload Policy](phases/phase-18-context-artifact-retention-and-upload-policy.md) |
| 19 | [Hypothesis Candidate Guidance](phases/phase-19-hypothesis-candidate-guidance.md) |
| 20 | [Mutmut Target Suggestions](phases/phase-20-mutmut-target-suggestions.md) |
| 21 | [CrossHair Candidate Guidance](phases/phase-21-crosshair-candidate-guidance.md) |
| 22 | [Cohesive Change Plans](phases/phase-22-cohesive-change-plans.md) |
| 23 | [Change-Budget Integration for Change Plans](phases/phase-23-change-budget-integration-for-change-plans.md) |
| 24 | [Integration Branch Series](phases/phase-24-integration-branch-series.md) |
| 25 | [Compression Backend Interface](phases/phase-25-compression-backend-interface.md) |
| 26 | [Optional Headroom Backend](phases/phase-26-optional-headroom-backend.md) |
| 27 | [Doctor Integration](phases/phase-27-doctor-integration.md) |
| 28 | [Examples and Proof Repos](phases/phase-28-examples-and-proof-repos.md) |
| 29 | [PR / GitHub Actions Summary Report](phases/phase-29-pr-github-actions-summary-report.md) |
| 30 | [Policy Packs and Onboarding Presets](phases/phase-30-policy-packs-and-onboarding-presets.md) |
| 31 | [Archguard Impact Analysis](phases/phase-31-archguard-impact-analysis.md) |
| 32 | [Repair Plan Command](phases/phase-32-repair-plan-command.md) |
| 33 | [Agent Adapter API](phases/phase-33-agent-adapter-api.md) |
| 34 | [Tach Architecture Contract Refit](phases/phase-34-tach-architecture-contract-refit.md) |
| 35 | [Static HTML Report](phases/phase-35-static-html-report.md) |
| 36 | [Review-Driven Stabilization Plan](phases/phase-36-review-driven-stabilization-plan.md) |
| 37 | [Headroom Backend Correctness](phases/phase-37-headroom-backend-correctness.md) |
| 38 | [Change-Plan Authority Over Legacy Overrides](phases/phase-38-change-plan-authority-over-legacy-overrides.md) |
| 39 | [Coverage Semantics Hardening](phases/phase-39-coverage-semantics-hardening.md) |
| 40 | [Exact Repair Facts From Structured Artifacts](phases/phase-40-exact-repair-facts-from-structured-artifacts.md) |
| 41 | [Beta Release Metadata Refresh](phases/phase-41-beta-release-metadata-refresh.md) |
| 42 | [Pre-Case-Study Hardening Plan](phases/phase-42-pre-case-study-hardening-plan.md) |
| 43 | [Context Package Boundary Split](phases/phase-43-context-package-boundary-split.md) |
| 44 | [Hook Output Invariant Tests](phases/phase-44-hook-output-invariant-tests.md) |
| 45 | [Release-Check Ergonomics](phases/phase-45-release-check-ergonomics.md) |
| 46 | [Release-State Drift Check](phases/phase-46-release-state-drift-check.md) |
| 57 | [Advisory Deep Mutation Sweep](phases/phase-57-advisory-deep-mutation-sweep.md) |
| 58 | [Quiet Verifier Output Contract](phases/phase-58-quiet-verifier-output-contract.md) |
| 59 | [Smarter Verification Cadence Guidance](phases/phase-59-smarter-verification-cadence-guidance.md) |
| 60 | [Dogfood Source-Checkout Drift Detection](phases/phase-60-dogfood-source-checkout-drift-detection.md) |
| 61 | [Run-Scoped Diagnostic Retention](phases/phase-61-run-scoped-diagnostic-retention.md) |
| 62 | [Duplicate Generated Artifact Detection](phases/phase-62-duplicate-generated-artifact-detection.md) |
| 63 | [Configured-Repo-Only Codex and Claude Hooks](phases/phase-63-configured-repo-only-codex-and-claude-hooks.md) |
| 64 | [Documentation and Generated Guidance Slimming](phases/phase-64-documentation-and-generated-guidance-slimming.md) |
| 65 | [Mutation Sweep Executor and Survivor Triage](phases/phase-65-mutation-sweep-executor-and-survivor-triage.md) |
| 66 | [Advisory Sweep Survivor Triage](phases/phase-66-advisory-sweep-survivor-triage.md) |
| 73 | [Release Polish, Debt Score Clarity, Mutation UX, and Cohesion](phases/phase-73-release-polish-debt-mutation-and-cohesion.md) |
| 74 | [Review-Driven Stabilization](phases/phase-74-review-driven-stabilization.md) |
| 75 | [Below-10 Debt And Strict Typing Ratchets](phases/phase-75-below-10-debt-and-strict-typing-ratchets.md) |

## Future Work

| Item | Detailed Spec |
|---|---|
| External Case Studies and Measured Proof Harness | [External Case Studies and Measured Proof Harness](future-work/external-case-studies-and-measured-proof-harness.md) |
| Monorepo / Multi-Package Support | [Monorepo / Multi-Package Support](future-work/monorepo-multi-package-support.md) |
| Team Policy Templates | [Team Policy Templates](future-work/team-policy-templates.md) |

## Completion

| Item | Detailed Spec |
|---|---|
| Final Definition of Done | [Final Definition of Done](final-definition-of-done.md) |
| First Action | [First Action](first-action.md) |
