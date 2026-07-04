# Completed Phases 124-144

This archive bucket preserves completed roadmap history so `docs/ROADMAP.md` stays focused on active work.

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

## Completed: Public First-Touch Docs Prose Polish

Polish the first-touch public docs so install, verification, diagnostics, and
context-pack behavior are readable without compressed prose or collapsed command
examples.

Detailed scope:

[`docs/roadmap/phases/phase-130-public-first-touch-docs-prose-polish.md`](roadmap/phases/phase-130-public-first-touch-docs-prose-polish.md)

Completed work:

- [x] Phase 130: Public First-Touch Docs Prose Polish

## Completed: TypeScript Real-Repo Reviewability Evidence

Strengthen the TypeScript/JavaScript maturation track with end-to-end
reviewability evidence from temporary Git repositories instead of only patched
reader fixtures.

Detailed scope:

[`docs/roadmap/phases/phase-131-typescript-real-repo-reviewability-evidence.md`](roadmap/phases/phase-131-typescript-real-repo-reviewability-evidence.md)

Completed work:

- [x] Phase 131: TypeScript Real-Repo Reviewability Evidence

## Completed: Provider Maturation Docs Prose Polish

Polish provider-status, TypeScript provider, multi-ecosystem policy, and
TypeScript maturation docs so the current polyglot posture is clear without
compressed prose or overclaiming provider maturity.

Detailed scope:

[`docs/roadmap/phases/phase-132-provider-maturation-docs-prose-polish.md`](roadmap/phases/phase-132-provider-maturation-docs-prose-polish.md)

Completed work:

- [x] Phase 132: Provider Maturation Docs Prose Polish

## Completed: Provider DocSync Evidence Ratchet

Extend DocSync dogfooding for provider docs by linking TypeScript maturation and
provider-status claims to durable source and test evidence.

Detailed scope:

[`docs/roadmap/phases/phase-133-provider-docsync-evidence-ratchet.md`](roadmap/phases/phase-133-provider-docsync-evidence-ratchet.md)

Completed work:

- [x] Phase 133: Provider DocSync Evidence Ratchet

## Completed: Critical Active Docs DocSync Coverage

Extend DocSync dogfooding beyond first-touch and provider pages by adding
evidence-backed claims for high-risk active docs that guide agent behavior,
setup recommendations, debt scoring, mutation workflows, context safety, and
multi-ecosystem reviewability.

Detailed scope:

[`docs/roadmap/phases/phase-134-critical-active-docsync-coverage.md`](roadmap/phases/phase-134-critical-active-docsync-coverage.md)

Completed work:

- [x] Phase 134: Critical Active Docs DocSync Coverage

## Completed: Remaining Active Docs DocSync Coverage

Finish the active-doc DocSync dogfooding pass by giving every active doc
overview path at least one evidence-backed claim and ratcheting tests so new
active docs cannot ship with only object markers.

Detailed scope:

[`docs/roadmap/phases/phase-135-remaining-active-docsync-coverage.md`](roadmap/phases/phase-135-remaining-active-docsync-coverage.md)

Completed work:

- [x] Phase 135: Remaining Active Docs DocSync Coverage

## Completed: TypeScript Advisory Threshold Config

Move TypeScript/JavaScript reviewability advisory thresholds from hard-coded
constants into beta config fields while keeping current behavior advisory-only
and non-blocking.

Detailed scope:

[`docs/roadmap/phases/phase-136-typescript-advisory-threshold-config.md`](roadmap/phases/phase-136-typescript-advisory-threshold-config.md)

Completed work:

- [x] Phase 136: TypeScript Advisory Threshold Config

## Completed: TypeScript Unsupported Surface Docs

Make the experimental TypeScript/JavaScript provider's unsupported package
manager, runner, framework, coverage, dependency, and security surfaces
explicit so users do not mistake experimental support for feature parity.

Detailed scope:

[`docs/roadmap/phases/phase-137-typescript-unsupported-surface-docs.md`](roadmap/phases/phase-137-typescript-unsupported-surface-docs.md)

Completed work:

- [x] Phase 137: TypeScript Unsupported Surface Docs

## Completed: TypeScript Package Shape Evidence

Add real Git repository reviewability evidence for common npm, pnpm, Vite, and
Vitest TypeScript/JavaScript project shapes without changing provider behavior
or making TypeScript reviewability blocking.

Detailed scope:

[`docs/roadmap/phases/phase-138-typescript-package-shape-evidence.md`](roadmap/phases/phase-138-typescript-package-shape-evidence.md)

Completed work:

- [x] Phase 138: TypeScript Package Shape Evidence

## Completed: TypeScript External Real-Repo Comparison

Record one external public TypeScript/JavaScript repository comparison for
`assess reviewability` so TypeScript provider maturation is not based only on
synthetic fixture repositories.

Detailed scope:

[`docs/roadmap/phases/phase-139-typescript-external-real-repo-comparison.md`](roadmap/phases/phase-139-typescript-external-real-repo-comparison.md)

Completed work:

- [x] Phase 139: TypeScript External Real-Repo Comparison

## Completed: TypeScript Node Boilerplate External Comparison

Broaden TypeScript reviewability evidence with a second public repository
comparison that includes a Node TypeScript boilerplate migration from Jest to
Vitest.

Detailed scope:

[`docs/roadmap/phases/phase-140-typescript-node-boilerplate-external-comparison.md`](roadmap/phases/phase-140-typescript-node-boilerplate-external-comparison.md)

Completed work:

- [x] Phase 140: TypeScript Node Boilerplate External Comparison

## Completed: Provider-Neutral File Baseline Controls

Design provider-neutral controls for simple file facts such as length, nonblank
lines, changed-file counts, changed-line counts, ignored/generated paths, and
ratcheted baselines across explicit file groups. Keep Python's existing
blocking checks unchanged, keep non-Python groups advisory by default, and do
not use Tach as the language-neutral architecture answer.

Detailed scope:

[`docs/roadmap/phases/phase-141-provider-neutral-file-baseline-controls.md`](roadmap/phases/phase-141-provider-neutral-file-baseline-controls.md)

Detailed spec:

[`docs/roadmap/provider-neutral-file-baselines.md`](roadmap/provider-neutral-file-baselines.md)

Completed work:

- [x] Phase 141: Provider-Neutral File Baseline Controls

## Completed: Runtime Telemetry And Dogfood Logging

Design a standards-aligned logging and telemetry path so Agent Maintainer can
debug dogfooding quality without making normal agent output noisier.

Detailed scope:

[`docs/roadmap/phases/phase-142-runtime-telemetry-dogfood-logging.md`](roadmap/phases/phase-142-runtime-telemetry-dogfood-logging.md)

Detailed spec:

[`docs/roadmap/runtime-telemetry-dogfood-logging.md`](roadmap/runtime-telemetry-dogfood-logging.md)

Completed work:

- [x] Phase 142: Runtime Telemetry And Dogfood Logging

## Completed: DocSync Explicit Object End Markers

Make DocSync documentation object scope explicit by adding object end markers
that mirror the existing evidence start/end marker discipline.

Detailed scope:

[`docs/roadmap/phases/phase-143-docsync-explicit-object-end-markers.md`](roadmap/phases/phase-143-docsync-explicit-object-end-markers.md)

Completed work:

- [x] Phase 143: DocSync Explicit Object End Markers

## Completed: Runtime Event Foundation

Implement first local structured runtime event foundation without adding OpenTelemetry making normal verifier output noisier.

Detailed scope:

[`docs/roadmap/phases/phase-144-runtime-event-foundation.md`](roadmap/phases/phase-144-runtime-event-foundation.md)

Completed work:

- [x] Phase 144: Runtime Event Foundation
