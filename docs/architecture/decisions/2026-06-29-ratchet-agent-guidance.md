# ADR: Ratchet Agent Guidance

## Context

Phase 15 needs generated agent-facing guidance for legacy ratchet repair loops.
The main Agent Maintainer guidance already summarizes active configuration, but
ratchet work needs more specific rules around target selection and safe context
expansion.

## Decision

Add `agent_maintainer.ratchet.guidance` to the runtime layer in `tach.toml`.
The existing `python3 -m agent_maintainer guidance` command remains the only
guidance command. When `ratchet_enabled = true`, it also writes and checks
`AGENTS.ratchet.md`.

The main guidance links to the ratchet sidecar only when ratchets are active.

## Alternatives Considered

A separate `ratchet guidance` command would keep the core guidance module smaller
but would add another setup step and make stale guidance easier to miss. Folding
the sidecar into the existing guidance command keeps one source of truth for
write and freshness checks.

## Consequences

Ratchet guidance becomes part of the normal `guidance --check` gate for repos
that enable ratchets. Future ratchet-specific instructions should update the
ratchet renderer rather than hand-editing `AGENTS.ratchet.md`.
