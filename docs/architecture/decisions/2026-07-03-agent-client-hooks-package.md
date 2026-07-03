# Architecture Decision: Agent Client Hooks Internal Package

Status: accepted

## What Changed?

Agent-client hook templates, configuration merge helpers, and install-planning
adapters move into a new internal package, `agent_client_hooks`. The product
package keeps compatibility shims under `agent_maintainer.hooks` and continues
to own runtime hook verification.

## Why Necessary?

Hook template/config generation is reusable infrastructure. Keeping it inside
`agent_maintainer.hooks` mixed static client configuration with verifier
runtime, audit logging, context assembly, and subprocess execution. The split
clarifies ownership while preserving the public `agent-maintainer hooks`
command surface.

## Why This Is Not Architecture Drift

The new package is lower-level and must not import `agent_maintainer`.
`agent_maintainer` may depend on `agent_client_hooks` as product orchestration,
but runtime verifier behavior remains product-owned. This preserves the
intended dependency direction from the internal package roadmap.

## Alternatives Considered

1. Keep hook templates inside `agent_maintainer.hooks`. Rejected because it
   leaves reusable template/config primitives coupled to runtime verification.
2. Move the entire hook runtime package. Rejected because runtime execution
   depends on Agent Maintainer config, audit logs, context packs, and verifier
   command semantics.
3. Remove compatibility shims immediately. Rejected because the first package
   extraction pass should preserve old import paths until callers and docs
   stabilize.

## Boundary Impact

- `agent_client_hooks` owns constants, templates, merge helpers, adapter
  models, adapter selection, and planned writes.
- `agent_maintainer.hooks` owns CLI orchestration, install execution, runtime
  verification, context handling, audit logging, and subprocess execution.
- Compatibility shims under `agent_maintainer.hooks.templates`,
  `agent_maintainer.hooks.adapters`, and `agent_maintainer.hooks.merge` remain
  for this pass.

## What Remains Forbidden?

- `agent_client_hooks` must not import `agent_maintainer`.
- Runtime hook verification must not move into the template package without a
  separate adapter decision.
- New agent clients should not be added as part of this extraction.

## Review Or Expiration Condition

Revisit after the internal package boundary refactor completes. At that point,
decide whether compatibility shims stay as supported internal paths or are
removed in a documented cleanup phase.
