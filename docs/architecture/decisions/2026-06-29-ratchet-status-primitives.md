# ADR: Ratchet Status Primitives

## Context

The context-safe legacy ratchet roadmap needs a baseline comparison model before
it can add baseline persistence, target ranking, generated guidance, and repair
plans.

## Decision

Add `agent_maintainer.ratchet` as a runtime package and assign
`agent_maintainer.ratchet.findings` and `agent_maintainer.ratchet.status` to the
runtime layer. Add `agent_maintainer.ratchet.models` to the models layer.

The status primitive compares normalized findings and reports:

- `new`
- `worsened`
- `unchanged`
- `improved`
- `resolved`

It normalizes current file-length and structure-cohesion findings, then reports
stale-baseline reasons from provenance and missing current findings. Existing
check modules do not import ratchet code.

## Alternatives Considered

The comparison logic could have lived inside the first CLI command, but that
would make later target ranking and generated guidance depend on command output.
Keeping status as a reusable runtime primitive gives later phases a stable typed
contract.

## Consequences

Later ratchet modules must normalize findings into the model package rather than
inventing separate comparison shapes. Additional Tach entries for collection,
persistence, and CLI modules will require updating this decision or adding a new
decision note.
