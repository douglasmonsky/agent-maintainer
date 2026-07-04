# Context Next Actions Boundary

## Status

Accepted.

## Context

Context-pack hook pointers need to rank surgical expansion commands from exact
repair facts before broad context commands. Keeping this ranking in
`agent_context.pack_rendering` pushed the renderer over the module-member
limit and mixed output formatting with command-selection policy.

## Decision

Add `agent_context.next_actions` for ranking context expansion commands.
`agent_context.pack_rendering` may depend on it when rendering compact repair
capsules, but the helper remains inside the reusable `agent_context` package
and does not depend on `agent_maintainer`.

## Consequences

- Context rendering stays below the module-member limit.
- The surgical expansion policy is testable without rendering a full pointer.
- Broad context commands remain available as fallbacks after narrower repair
  fact commands.

## Alternatives Considered

- Keep the helpers in `pack_rendering`. Rejected because it weakens cohesion and
  trips the configured module-member cap.
- Raise or suppress the module-member cap. Rejected because the cap correctly
  identified a small boundary split.
