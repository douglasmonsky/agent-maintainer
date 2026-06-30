# Roadmap Guide

This directory contains detailed implementation specs for the current Agent
Maintainer roadmap. The root roadmap at [`../ROADMAP.md`](../ROADMAP.md) is only
a recovery checklist. It is useful for seeing the next phase, but it is not
enough to implement a phase correctly.

## Canonical Spec Layout

The canonical index is:

[`full-roadmap-blueprint.md`](full-roadmap-blueprint.md)

The index must stay small. It links to:

- [`overview.md`](overview.md) for mission, baseline, target architecture, and
  execution rules;
- [`phases/`](phases/) for detailed implementation specs;
- [`future-work/`](future-work/) for postponed work;
- [`final-definition-of-done.md`](final-definition-of-done.md) for completion
  criteria.

Do not re-expand the index into a monolithic blueprint. If a phase needs more
detail, update that phase file.

## Resume Workflow

Before starting or resuming a roadmap phase:

1. Check the current phase in [`../ROADMAP.md`](../ROADMAP.md).
2. Open [`full-roadmap-blueprint.md`](full-roadmap-blueprint.md).
3. Open the matching file in [`phases/`](phases/), for example:

   ```bash
   rg -n "Phase 64" docs/roadmap/phases
   ```

4. Read the full phase section before changing files.
5. Implement one phase per PR unless the user explicitly changes that rule.
6. Update [`../ROADMAP.md`](../ROADMAP.md) only after the phase is implemented,
   tested, merged, and confirmed in post-merge CI.

If the checklist and split phase spec disagree, treat the phase spec as the
source of truth and update the checklist in the same PR that resolves the
mismatch.

## Recovery

The split blueprint is intentionally vendored into the repository so work can
resume after chat compaction, handoff, or local context loss without relying on
external attachments.

If the split files appear missing or stale, restore the source document named
`agent-maintainer-full-roadmap-blueprint.md`, split it back into
`docs/roadmap/phases/`, and keep `full-roadmap-blueprint.md` as a compact index.
