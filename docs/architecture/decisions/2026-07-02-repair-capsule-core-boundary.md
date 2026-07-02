# Repair Capsule Core Boundary

## Status

Accepted.

## Context

Phase 108 adds a strict agent-facing repair capsule for failed verifier output.
The existing `agent_maintainer.core.reporting` module already owned compact
terminal printing and structured-artifact summaries. Adding capsule assembly
there pushed the module over the configured member limit and mixed two
responsibilities: summarizing tool artifacts and constructing the output
contract agents consume.

## Decision

Create `agent_maintainer.core.repair_capsule` for the strict repair-capsule
contract. It owns the result/profile/run-id header, top repair facts, likely
next action, and single expansion command. `core.reporting` remains the terminal
printer and delegates failure-capsule line construction to this module.

`repair_capsule` may depend on `reporting_context` for safe expansion commands.
It must not own verifier execution, artifact writing, context-pack building, or
hook-client behavior.

## Consequences

- The repair capsule has a dedicated boundary and tests can target it directly.
- `core.reporting` stays under the module-member limit.
- Agent-facing output changes can evolve without mixing into structured
  artifact parsers.
- Tach explicitly records `reporting -> repair_capsule -> reporting_context`.

## Alternatives Considered

- Keep capsule helpers in `core.reporting`: rejected because it exceeded the
  module-member limit and weakened cohesion.
- Move capsule rendering into context-pack code: rejected because verifier
  failure output should not depend on context-pack generation.
- Put capsule rendering in hooks: rejected because the same contract is needed
  for normal verifier output and hook output.
