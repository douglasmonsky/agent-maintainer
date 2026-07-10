# Completed Phases 109-123

This archive bucket preserves completed roadmap history so `docs/ROADMAP.md` stays focused on active work.

## Completed: Internal Package Boundary Refactor Roadmap

Agent Maintainer should split reusable primitives into internal packages only
after baseline characterization and package-boundary instructions are durable.
This phase adds the separate roadmap and preserves the exact implementation
handoff without moving runtime code.

Detailed scope:

[`docs/roadmap/phases/phase-109-internal-package-boundary-roadmap.md`](../phases/phase-109-internal-package-boundary-roadmap.md)

Detailed roadmap:

[`docs/roadmap/internal-package-boundaries.md`](../internal-package-boundaries.md)

Exact instructions:

[`docs/roadmap/internal-package-boundaries-implementation-guide.txt`](../internal-package-boundaries-implementation-guide.txt)

Completed work:

- [x] Phase 109: Internal Package Boundary Refactor Roadmap

## Completed: Internal Package Baseline And Ownership

Before moving runtime code into extracted internal packages, Agent Maintainer
captured current behavior and accepted the package ownership dependency
direction. DocSync now owns the docs/evidence boundary that earlier planning
called `docs_evidence`.

Detailed scope:

[`docs/roadmap/phases/phase-110-internal-package-baseline-and-ownership.md`](../phases/phase-110-internal-package-baseline-and-ownership.md)

Architecture decision:

[`docs/architecture/decisions/2026-07-02-internal-package-ownership.md`](../../architecture/decisions/2026-07-02-internal-package-ownership.md)

Completed work:

- [x] Phase 110: Internal Package Baseline And Ownership

## Completed: Agent Repair Facts Internal Package Extraction

Agent Maintainer should extract repair-fact payload normalization, parser
implementations, and parser dispatch into a new internal package,
`agent_repair_facts`, while preserving current context-pack behavior and old
import paths through compatibility shims.

Detailed scope:

[`docs/roadmap/phases/phase-111-agent-repair-facts-package.md`](../phases/phase-111-agent-repair-facts-package.md)

Internal package roadmap:

[`docs/roadmap/internal-package-boundaries.md`](../internal-package-boundaries.md)

Implementation guide:

[`docs/roadmap/internal-package-boundaries-implementation-guide.txt`](../internal-package-boundaries-implementation-guide.txt)

Completed work:

- [x] Phase 111: Agent Repair Facts Internal Package Extraction

## Completed: Agent Context Primitives And Reading Extraction

Agent Maintainer should begin the `agent_context` package extraction by moving
pure context primitives and reading utilities first, leaving product-coupled
context-pack CLI, ratchet, and verifier-artifact adapter work for follow-up.

Detailed scope:

[`docs/roadmap/phases/phase-112-agent-context-primitives.md`](../phases/phase-112-agent-context-primitives.md)

Internal package roadmap:

[`docs/roadmap/internal-package-boundaries.md`](../internal-package-boundaries.md)

Implementation guide:

[`docs/roadmap/internal-package-boundaries-implementation-guide.txt`](../internal-package-boundaries-implementation-guide.txt)

Completed work:

- [x] Phase 112: Agent Context Primitives And Reading Extraction

## Completed: Agent Run Artifacts Internal Package Extraction

Agent Maintainer should next extract verifier artifact schemas and rendering
helpers into `agent_run_artifacts`, preserving `.verify-logs` behavior, old
`agent_maintainer.verify.*` import paths, PR summary output, and run-scoped
diagnostic layout.

Detailed scope:

[`docs/roadmap/phases/phase-113-agent-run-artifacts-package.md`](../phases/phase-113-agent-run-artifacts-package.md)

Internal package roadmap:

[`docs/roadmap/internal-package-boundaries.md`](../internal-package-boundaries.md)

Implementation guide:

[`docs/roadmap/internal-package-boundaries-implementation-guide.txt`](../internal-package-boundaries-implementation-guide.txt)

Completed work:

- [x] Phase 113: Agent Run Artifacts Internal Package Extraction

## Completed: DocSync Dogfood Seed And Ratchet

DocSync should start dogfooding this repository on its own durable extraction
contract before broader docs coverage. This keeps the trace useful while the
package-extraction refactor is still moving.

Detailed scope:

[`docs/roadmap/phases/phase-114-docsync-dogfood-ratchet.md`](../phases/phase-114-docsync-dogfood-ratchet.md)

Completed work:

- [x] Phase 114: DocSync Dogfood Seed And Ratchet

## Completed: Agent Client Hooks Internal Package Extraction

Agent Maintainer should extract agent-client hook templates, merge helpers, and
install planning into `agent_client_hooks`, while keeping hook runtime
verification product-owned under `agent_maintainer.hooks`.

Detailed scope:

[`docs/roadmap/phases/phase-115-agent-client-hooks-package.md`](../phases/phase-115-agent-client-hooks-package.md)

Completed work:

- [x] Phase 115: Agent Client Hooks Internal Package Extraction

## Completed: Internal Package Boundary Regression Tests

Extracted internal packages should have executable dependency-direction checks
in addition to Tach domain contracts. This keeps future extraction work from
quietly importing product orchestration back into reusable packages.

Detailed scope:

[`docs/roadmap/phases/phase-116-internal-package-boundary-tests.md`](../phases/phase-116-internal-package-boundary-tests.md)

Completed work:

- [x] Phase 116: Internal Package Boundary Regression Tests

## Completed: README DocSync Evidence Ratchet

DocSync should now dogfood public documentation, not only its extraction note.
Start with README claims that users rely on during first adoption and repair
loops.

Detailed scope:

[`docs/roadmap/phases/phase-117-readme-docsync-evidence.md`](../phases/phase-117-readme-docsync-evidence.md)

Completed work:

- [x] Phase 117: README DocSync Evidence Ratchet

## Completed: Agent Context Pack Rendering Extraction

Continue internal package boundary refactor by moving pure context-pack
rendering and sanitizing helpers into `agent_context`, while keeping context
builder, compression, ratchet, and CLI orchestration product-owned.

Detailed scope:

[`docs/roadmap/phases/phase-118-agent-context-pack-rendering.md`](../phases/phase-118-agent-context-pack-rendering.md)

Completed work:

- [x] Phase 118: Agent Context Pack Rendering Extraction

## Completed: Agent Context Compression Extraction

Move reusable context compression primitives into `agent_context`, while keeping
context-pack compression orchestration, CLI/config behavior, and artifact
generation product-owned.

Detailed scope:

[`docs/roadmap/phases/phase-119-agent-context-compression.md`](../phases/phase-119-agent-context-compression.md)

Completed work:

- [x] Phase 119: Agent Context Compression Extraction

## Completed: Public Docs DocSync Ratchet

Expand DocSync from README-only dogfooding into the core public docs users
and agents follow during adoption, verification, diagnostics, ratcheting,
scan selection, and provider-status review.

Detailed scope:

[`docs/roadmap/phases/phase-120-docsync-public-docs-ratchet.md`](../phases/phase-120-docsync-public-docs-ratchet.md)

Completed work:

- [x] Phase 120: Public Docs DocSync Ratchet

## Completed: Operational DocSync Trace Closure

Close the stale roadmap gap after extending DocSync trace coverage into agent
hooks, context compression, release checklist, and architecture policy docs.

Detailed scope:

[`docs/roadmap/phases/phase-121-operational-docsync-trace-closure.md`](../phases/phase-121-operational-docsync-trace-closure.md)

Completed work:

- [x] Phase 121: Operational DocSync Trace Closure

## Completed: Provider-Specific DocSync Evidence

Extend DocSync dogfooding into provider-specific public docs for the active
TypeScript/JavaScript maturation track. This keeps provider docs tied to source
and test evidence while avoiding new ecosystem scope. Detailed scope:

[`docs/roadmap/phases/phase-122-provider-specific-docsync-evidence.md`](../phases/phase-122-provider-specific-docsync-evidence.md)

Completed work:

- [x] Phase 122: Provider-Specific DocSync Evidence

## Completed: Internal Package Refactor Docs Closure

Close stale recovery gap in internal-package refactor docs after extraction
phases landed. Future agents should see current package shape and remaining
invariants instead of instructions implying Phase 0 still needs to start.

Detailed scope:

[`docs/roadmap/phases/phase-123-internal-package-refactor-docs-closure.md`](../phases/phase-123-internal-package-refactor-docs-closure.md)

Completed work:

- [x] Phase 123: Internal Package Refactor Docs Closure
