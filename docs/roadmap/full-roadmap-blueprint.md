# Agent Maintainer Roadmap Blueprint

This compact roadmap index points to split specs under `docs/roadmap`; use `docs/ROADMAP.md` as the recovery checklist. Do not re-expand index into monolithic blueprint.

## Overview

- [Mission, baseline, architecture target, execution rules](overview.md)
- [Polyglot Ecosystem Provider Roadmap](polyglot-ecosystem-providers.md)
- [Final Definition Done](final-definition-of-done.md)

## Phases

| Phase | Detailed Spec |
| ---: | --- |
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
| 67 | [Public Docs, Setup Advisor, and Technical Debt Score](phases/phase-67-public-docs-onboarding-and-debt-score.md) |
| 73 | [Release Polish, Debt Score Clarity, Mutation UX, and Cohesion](phases/phase-73-release-polish-debt-mutation-and-cohesion.md) |
| 74 | [Review-Driven Stabilization Metadata, Schedules, and Output Contracts](phases/phase-74-review-driven-stabilization.md) |
| 75 | [Below-10 Debt And Strict Typing Ratchets](phases/phase-75-below-10-debt-and-strict-typing-ratchets.md) |
| 76 | [Ecosystem Provider Roadmap](phases/phase-76-ecosystem-provider-roadmap.md) |
| 77 | [Ecosystem Provider Characterization Safety Net](phases/phase-77-ecosystem-provider-characterization-safety-net.md) |
| 78 | [Minimal Internal Python Provider Seam](phases/phase-78-minimal-internal-python-provider-seam.md) |
| 79 | [Global And Ecosystem Check Ownership](phases/phase-79-global-and-ecosystem-check-ownership.md) |
| 80 | [Generic File Classification, Python Only](phases/phase-80-generic-file-classification-python-only.md) |
| 81 | [Policy Checks Through Python Classifier Adapters](phases/phase-81-policy-checks-through-python-classifier-adapters.md) |
| 82 | [Neutral Config Path Exploration](phases/phase-82-neutral-config-path-exploration.md) |
| 83 | [Experimental TypeScript/JavaScript Provider](phases/phase-83-experimental-typescript-javascript-provider.md) |
| 84 | [TypeScript Provider Doctor Hints And Fixture Smoke Tests](phases/phase-84-typescript-provider-doctor-hints-and-fixtures.md) |
| 85 | [TypeScript Structured Output Repair Facts](phases/phase-85-typescript-structured-output-repair-facts.md) |
| 86 | [Provider Contribution Guide](phases/phase-86-provider-contribution-guide.md) |
| 88 | [Provider API Stability Decision](phases/phase-88-provider-api-stability-decision.md) |
| 89 | [Measured Repair Case Studies](phases/phase-89-measured-repair-case-studies.md) |
| 90 | [Workspace Config Foundation](phases/phase-90-workspace-config-foundation.md) |
| 91 | [Team Policy Templates](phases/phase-91-team-policy-templates.md) |
| 92 | [Roadmap Future Work Cleanup](phases/phase-92-roadmap-future-work-cleanup.md) |
| 93 | [Provider Stabilization And Doctor Alignment](phases/phase-93-provider-stabilization-and-doctor-alignment.md) |
| 94 | [Multi-Ecosystem Reviewability Policy Design](phases/phase-94-multi-ecosystem-reviewability-policy-design.md) |
| 95 | [Provider-Aware File Change Classification](phases/phase-95-provider-aware-file-change-classification.md) |
| 96 | [Advisory Reviewability Assessment](phases/phase-96-advisory-reviewability-assessment.md) |
| 97 | [Advisory Ecosystem Suppression Classification](phases/phase-97-advisory-ecosystem-suppression-classification.md) |
| 98 | [TypeScript Reviewability Fixture Evidence](phases/phase-98-typescript-reviewability-fixture-evidence.md) |
| 99 | [Advisory Provider Reviewability Summaries](phases/phase-99-advisory-provider-reviewability-summaries.md) |
| 100 | [TypeScript Provider Maturation](phases/phase-100-typescript-provider-maturation.md) |
| 101 | [TypeScript Advisory Threshold Evidence](phases/phase-101-typescript-advisory-threshold-evidence.md) |
| 102 | [TypeScript Setup Advisor Recommendations](phases/phase-102-typescript-setup-advisor.md) |
| 104 | [TypeScript Test Repair Facts](phases/phase-104-typescript-test-repair-facts.md) |
| 105 | [Provider Dispatch Registry](phases/phase-105-provider-dispatch-registry.md) |
| 106 | [Archive Go Provider History Out Of Main](phases/phase-106-archive-go-provider-history.md) |
| 107 | [Roadmap Status Label Cleanup](phases/phase-107-roadmap-status-label-cleanup.md) |
| 108 | [Repair Capsule Output Contract And Pointer-First Context](phases/phase-108-repair-capsule-output-contract.md) |
| 109 | [Internal Package Boundary Refactor Roadmap](phases/phase-109-internal-package-boundary-roadmap.md) |
| 110 | [Internal Package Baseline And Ownership](phases/phase-110-internal-package-baseline-and-ownership.md) |
| 111 | [Agent Repair Facts Internal Package Extraction](phases/phase-111-agent-repair-facts-package.md) |
| 112 | [Agent Context Primitives And Reading Extraction](phases/phase-112-agent-context-primitives.md) |
| 113 | [Agent Run Artifacts Internal Package Extraction](phases/phase-113-agent-run-artifacts-package.md) |
| 114 | [DocSync Dogfood Seed And Ratchet](phases/phase-114-docsync-dogfood-ratchet.md) |
| 115 | [Agent Client Hooks Internal Package Extraction](phases/phase-115-agent-client-hooks-package.md) |
| 116 | [Internal Package Boundary Regression Tests](phases/phase-116-internal-package-boundary-tests.md) |
| 117 | [README DocSync Evidence Ratchet](phases/phase-117-readme-docsync-evidence.md) |
| 118 | [Agent Context Pack Rendering Extraction](phases/phase-118-agent-context-pack-rendering.md) |
| 119 | [Agent Context Compression Extraction](phases/phase-119-agent-context-compression.md) |
| 120 | [Public Docs DocSync Ratchet](phases/phase-120-docsync-public-docs-ratchet.md) |
| 121 | [Operational DocSync Trace Closure](phases/phase-121-operational-docsync-trace-closure.md) |
| 122 | [Provider-Specific DocSync Evidence](phases/phase-122-provider-specific-docsync-evidence.md) |
| 123 | [Internal Package Refactor Docs Closure](phases/phase-123-internal-package-refactor-docs-closure.md) |
| 124 | [DocSync Foundation Roadmap Closure](phases/phase-124-docsync-foundation-roadmap-closure.md) |
| 125 | [Roadmap Blueprint Index Repair](phases/phase-125-roadmap-blueprint-index-repair.md) |
| 126 | [Roadmap Overview Current State](phases/phase-126-roadmap-overview-current-state.md) |
| 127 | [Git Metadata Duplicate Artifact Warning](phases/phase-127-git-metadata-duplicate-artifact-warning.md) |
| 128 | [Active DocSync Coverage Ratchet](phases/phase-128-active-docsync-coverage-ratchet.md) |
| 129 | [Mutation Results Artifact Fallback](phases/phase-129-mutation-results-artifact-fallback.md) |
| 130 | [Public First-Touch Docs Prose Polish](phases/phase-130-public-first-touch-docs-prose-polish.md) |
| 131 | [TypeScript Real-Repo Reviewability Evidence](phases/phase-131-typescript-real-repo-reviewability-evidence.md) |
| 132 | [Provider Maturation Docs Prose Polish](phases/phase-132-provider-maturation-docs-prose-polish.md) |
| 133 | [Provider DocSync Evidence Ratchet](phases/phase-133-provider-docsync-evidence-ratchet.md) |
| 134 | [Critical Active Docs DocSync Coverage](phases/phase-134-critical-active-docsync-coverage.md) |
| 135 | [Remaining Active Docs DocSync Coverage](phases/phase-135-remaining-active-docsync-coverage.md) |
| 136 | [TypeScript Advisory Threshold Config](phases/phase-136-typescript-advisory-threshold-config.md) |

## Future Work

- [Future Work: External Case Studies and Measured Proof Harness](future-work/external-case-studies-and-measured-proof-harness.md)
- [Future Work: Monorepo / Multi-Package Support](future-work/monorepo-multi-package-support.md)
- [Future Work: Team Policy Templates](future-work/team-policy-templates.md)
