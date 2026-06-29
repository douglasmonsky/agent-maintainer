# Roadmap Guide

This directory contains the detailed implementation specification for the
current Agent Maintainer roadmap.

The root roadmap at [`../ROADMAP.md`](../ROADMAP.md) is only a recovery
checklist. It is useful for seeing which phase is next, but it is not enough to
implement a phase correctly.

Before starting any roadmap phase:

1. Open [`full-roadmap-blueprint.md`](full-roadmap-blueprint.md).
2. Read the matching phase section end to end.
3. Follow that phase's scope, file targets, tests, documentation requirements,
   acceptance criteria, and out-of-scope rules.
4. Update the checklist in [`../ROADMAP.md`](../ROADMAP.md) only after the
   phase is implemented, tested, merged, and confirmed in CI.

If the checklist and the blueprint disagree, treat the blueprint as the source
of truth and update the checklist in the same PR that resolves the mismatch.

The blueprint was intentionally vendored into this repository so work can
resume after chat compaction, handoff, or local context loss without relying on
external attachments.
