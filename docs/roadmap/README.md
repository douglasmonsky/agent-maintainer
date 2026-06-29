# Roadmap Guide

This directory contains the detailed implementation specification for the
current Agent Maintainer roadmap.

The root roadmap at [`../ROADMAP.md`](../ROADMAP.md) is only a recovery
checklist. It is useful for seeing the next phase, but it is not enough to
implement a phase correctly.

## Canonical Spec

The full implementation blueprint is checked into the repository as
[`full-roadmap-blueprint.md`](full-roadmap-blueprint.md). That file is the
source of truth for phase scope, file targets, tests, documentation
requirements, acceptance criteria, and out-of-scope rules.

Do not implement roadmap phase checklist alone.

## Resume Workflow

Before starting or resuming a roadmap phase:

1. Check the current phase in [`../ROADMAP.md`](../ROADMAP.md).
2. Search the full blueprint phase heading, for example:
   `rg -n "Phase 24" docs/roadmap/full-roadmap-blueprint.md`.
3. Read the full phase section before changing files.
4. Implement one phase per PR unless the user explicitly changes that rule.
5. Update the checklist in [`../ROADMAP.md`](../ROADMAP.md) only after the
   phase is implemented, tested, merged, and confirmed in post-merge CI.

If the checklist and blueprint disagree, treat the blueprint as source of truth
and update the checklist in the same PR that resolves the mismatch. If the
blueprint appears missing or stale, restore the source document named
`agent-maintainer-full-roadmap-blueprint.md` before continuing implementation.

The blueprint is intentionally vendored into the repository so work can resume
after chat compaction, handoff, or local context loss without relying on
external attachments.
