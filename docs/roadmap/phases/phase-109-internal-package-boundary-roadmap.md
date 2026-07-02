# Phase 109: Internal Package Boundary Refactor Roadmap

## Status

Completed.

## Goal

Create a separate, durable roadmap for the internal package-boundary refactor so
future work can proceed cautiously without mixing file moves into unrelated
repair-capsule, DocSync, or roadmap cleanup changes.

## Scope

- Preserve the exact external handoff instructions in a dedicated reference
  file.
- Add a summarized roadmap for the refactor phases and invariants.
- Link the new roadmap from the main roadmap and blueprint.
- Do not move runtime code as part of this phase.

## Non-Goals

- No extraction of `agent_repair_facts`, `agent_context`,
  `agent_run_artifacts`, `agent_client_hooks`, or `docs_evidence`.
- No public packaging change.
- No compatibility shim changes.
- No Tach package-boundary changes beyond links to the future plan.

## Deliverables

- [`docs/roadmap/internal-package-boundaries.md`](../internal-package-boundaries.md)
- [`docs/roadmap/internal-package-boundaries-implementation-guide.txt`](../internal-package-boundaries-implementation-guide.txt)
- Main roadmap and blueprint links.

## Acceptance Criteria

- The refactor has a separate roadmap from active product phases.
- The exact implementation instructions are available without summarization
  loss.
- The roadmap states hard invariants, phase order, caution points, and the
  Phase 0 first action.
- No runtime behavior changes are introduced by this planning phase.

## Verification

- `npx --no-install markdownlint-cli2 docs/roadmap/internal-package-boundaries.md docs/roadmap/phases/phase-109-internal-package-boundary-roadmap.md`
- `git diff --check`
