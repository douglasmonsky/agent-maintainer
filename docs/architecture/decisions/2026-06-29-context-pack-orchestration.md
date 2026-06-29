# Context Pack Orchestration Boundary

## Status

Accepted.

## Context

Phase 16 adds `agent_maintainer.context.packs`, which builds bounded repair
context packs from existing verifier failure records, selected logs, safe file
outlines, and ratchet target state. It also adds
`agent_maintainer.context.pack_rendering` to render the pack payload into
Markdown and JSON.

## Decision

Assign `agent_maintainer.context.packs` to the Tach orchestration layer.
Assign `agent_maintainer.context.pack_rendering` to the runtime layer.

The pack module coordinates lower-level context and ratchet helpers and writes
pack artifacts. The rendering module owns the final handoff format and budget
suffix logic. Neither module defines new scanner policy or owns the low-level
file/log safety rules.

## Alternatives Considered

- Put pack generation in `agent_maintainer.context.cli`: rejected because it
  would make the CLI module own artifact generation and harder to test.
- Put pack generation in runtime context modules: rejected because it depends on
  multiple runtime capabilities and ratchet summaries rather than one primitive.

## Still Forbidden

The lower-level file, log, diff, and failure helpers should not import the pack
or CLI modules. Pack generation may compose those helpers, but context safety
rules should remain in the runtime/shared modules where they are easier to test
independently.
