# Wait Runtime Events Boundary

## Status

Accepted.

## Context

Agent efficacy assessment needs explicit wait polling events to distinguish
healthy use of repository waiters from manual check polling. The quiet wait
adapters should stay small and reusable, and should not learn repository
configuration or runtime event sinks.

## Decision

`agent_maintainer.wait.cli` may depend on
`agent_maintainer.runtime_events.waiting` to emit compact local `wait.poll`
events for CLI-driven waits. The lower-level wait modules (`github`,
`github_pr`, and `verifier`) only expose optional poll callbacks and remain
independent of runtime event configuration.

## Why This Is Not Architecture Drift

The dependency is limited to the CLI orchestration layer, where command-scoped
runtime events already belong. Polling logic remains in the wait domain, while
event sink setup remains in the runtime events domain.

## Alternatives Considered

- Put runtime event sink loading directly in wait adapters. Rejected because it
  would couple pure polling modules to repository configuration.
- Emit only top-level `command.finished` events. Rejected because it cannot show
  whether waiters owned polling during long-running work.
- Use Tach ignores. Rejected because the boundary is intentional and should be
  documented.

## Still Forbidden

Wait adapter modules must not import runtime event sinks or repository
configuration directly. Runtime event payloads must remain compact, local, and
free of raw command arguments or secrets.
